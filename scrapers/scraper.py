#!/usr/bin/env python3
"""Usage: python3 <name>.py [-s] [-u] [-v] [-q] FAMILY
   Output: Outputs data (necessary for the family visualizer) for languages in FAMILY to json files
"""

from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as etree
import argparse
import re
import logging
import json
import os
import subprocess
import shutil
import requests

from lexccounter import countStems as countLexcStems
from dixcounter import get_info as countDixStems

SCRAPERS_DIR = Path(__file__).absolute().parent
ROOT_DIR = SCRAPERS_DIR.parent
JSON_DIR = ROOT_DIR.joinpath("json")
REPOS_DIR = SCRAPERS_DIR.joinpath("git-repos")

iso3to2 = json.load(open(SCRAPERS_DIR.joinpath("iso3to2.json"), "r"))

pairLocations = ["incubator", "nursery", "staging", "trunk"]
langLocations = ["languages", "incubator"]


def rmPrefix(word):
    """Removes the apertium- prefix"""
    return word[len("apertium-") :]


def prepRepo(repo, quiet):
    """Adds repo if it doesn't exist, or updates it if does, and copies .mailmap to it"""
    if not REPOS_DIR.joinpath(repo).exists():
        if not quiet:
            print("Cloning {}...".format(repo), flush=True)
            # Replaces the multi-line git clone status check with a sigle-line message
        subprocess.call(
            ["git", "clone", "--quiet", "https://github.com/apertium/{}".format(repo),],
            cwd=REPOS_DIR,
        )
    else:
        subprocess.call(
            ["git", "pull", "--force", "--quiet",], cwd=REPOS_DIR.joinpath(repo),
        )
    shutil.copyfile(
        SCRAPERS_DIR.joinpath(".mailmap"), REPOS_DIR.joinpath(repo, ".mailmap"),
    )


def fileExt(repo):
    """Returns the extension of the dictionary.
    Useful for monolinguals, that can have a .lexc, .dix or .metadix extension"""
    for file in sorted(
        REPOS_DIR.joinpath("apertium-{0}".format(repo)).glob(
            "apertium-{0}.{0}.*".format(repo)
        )
    ):
        if file.suffix in (".lexc", ".dix", ".metadix"):
            return file.suffix.replace(".", "")
    return "unknown"


def monoHistory(language, quiet):
    """Returns the history of a monolingual dictionary"""
    dirName = "apertium-{}".format(language)
    try:
        oldFile = json.load(open(JSON_DIR.joinpath("{}.json".format(language)), "r"))
        for data in oldFile:
            if data["name"] == language:
                history = data["history"]
                break
            history = []
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        history = []
    prepRepo(dirName, quiet)
    extension = fileExt(language)
    commits = (
        subprocess.check_output(
            [
                "git",
                "log",
                "--format=%H %aN %aI",
                "--follow",
                "apertium-{0}.{0}.{1}".format(language, extension),
            ],
            cwd=REPOS_DIR.joinpath(dirName),
        )
        .decode("utf-8")
        .split("\n")
    )

    commits.pop()  # last line is always empty
    for commit in commits:
        data = commit.split(" ")
        commitData = {
            "sha": data[0],
            "author": " ".join(data[1:-1]),
            "date": data[-1],
        }

        if any(commitData["sha"] == cm["sha"] for cm in history):
            continue

        fileURL = "https://raw.githubusercontent.com/apertium/apertium-{0}/{1}/apertium-{0}.{0}.{2}".format(
            language, commitData["sha"], extension
        )
        dataFile = requests.get(fileURL)
        if not dataFile:
            fileURL = "https://raw.githubusercontent.com/apertium/apertium-{0}/{1}/apertium-{0}.{0}.{2}".format(
                iso3to2[language], commitData["sha"], extension
            )
            dataFile = requests.get(fileURL)

        if extension == "lexc":
            try:
                stems = countLexcStems(dataFile.text)
            except SystemExit:
                logging.getLogger("monoHistory").warning(
                    "Unable to count lexc stems for %s in commit %s",
                    language,
                    commitData["sha"],
                )
                continue
        else:
            stems = countDixStems(fileURL, False)
            if stems == -1:
                logging.getLogger("monoHistory").warning(
                    "Unable to count dix stems for %s in commit %s",
                    language,
                    commitData["sha"],
                )
                continue
            stems = stems["stems"]

        commitData["stems"] = stems
        history.append(commitData)

    return {"name": language, "history": history}


def pairHistory(language, languages, packages, quiet):
    """Returns the history of all pairs of a language"""
    langPackages = []
    for package in packages:
        if not (
            language in package["name"]
            and re.match(r"apertium-\w+-\w+", package["name"])
        ):
            continue

        dirName = package["name"]
        pairName = rmPrefix(dirName)
        pairList = pairName.split("-")
        if (
            not set(pairList) <= set(languages) or pairName == "ita-srd"
        ):  # This repo exists as srd-ita and ita-srd is empty
            continue

        if not quiet:
            print("Getting commits for {}...".format(dirName), flush=True)

        prepRepo(dirName, quiet)
        dixName = (
            pairName if pairName != "tat-kir" else "tt-ky"
        )  # The tat-kir bidix is still named according to iso639-1 standards

        commits = (
            subprocess.check_output(
                [
                    "git",
                    "log",
                    "--format=%H %aN %aI",
                    "--follow",
                    "apertium-{0}.{0}.dix".format(dixName),
                ],
                cwd=REPOS_DIR.joinpath(dirName),
            )
            .decode("utf-8")
            .split("\n")
        )

        try:
            oldFile = json.load(
                open(JSON_DIR.joinpath("{}.json".format(language)), "r")
            )
            for data in oldFile:
                if data["name"] == pairName:
                    history = data["history"]
                    break
                history = []
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            history = []

        commits.pop()  # Last line is always empty
        for commit in commits:
            commitData = {}
            data = commit.split(" ")
            commitData["sha"] = data[0]
            commitData["author"] = " ".join(data[1:-1])
            commitData["date"] = data[-1]

            if any(commitData["sha"] == cm["sha"] for cm in history):
                continue

            dixFile = "https://raw.githubusercontent.com/apertium/apertium-{0}/{1}/apertium-{0}.{0}.dix".format(
                pairName, commitData["sha"]
            )
            stems = countDixStems(dixFile, True)
            if stems == -1:
                dixName = iso3to2[pairList[0]] + "-" + iso3to2[pairList[1]]
                dixFile = "https://raw.githubusercontent.com/apertium/apertium-{0}/{2}/apertium-{1}.{1}.dix".format(
                    pairName, dixName, commitData["sha"]
                )
                stems = countDixStems(dixFile, True)
                if stems == -1:
                    logging.getLogger("pairHistory").warning(
                        "Unable to count dix stems for %s in commit %s",
                        pairName,
                        commitData["sha"],
                    )
                    continue

            commitData["stems"] = stems["stems"]
            history.append(commitData)

        langPackages.append({"name": pairName, "history": history})
    return langPackages


def monoData(packages, languages, langFamily, updatemailmap, quiet):
    """Returns data for all monolingual dictionaries: state, stems, location and contributors"""
    data = []
    for package in packages:
        if not (
            re.match(r"apertium-\w+$", package["name"])
            and rmPrefix(package["name"]) in languages
        ):
            continue

        dirName = package["name"]
        language = rmPrefix(dirName)
        prepRepo(dirName, quiet)
        extension = fileExt(language)
        if extension == "lexc":
            fileType = extension
        elif extension == "dix":  # extension is dix, but type is monodix
            fileType = "monodix"
        else:
            fileType = "metamonodix"  # extension is metadix, but type is metamonodix

        try:
            stats = requests.get(
                "https://apertium.projectjj.com/stats-service/{}/{}/".format(
                    dirName, fileType
                )
            ).json()["stats"]
        except KeyError:
            raise Exception(
                "The stats-service seems to be updating at the moment. Please try again later"
            )
            # Raises an exception because the script can't continue
        for statistic in stats:
            if statistic["stat_kind"] == "Stems":
                stems = statistic["value"]
                break
        for topic in package["topics"]:
            if rmPrefix(topic) in langLocations:
                location = rmPrefix(topic)
                break

        lines = subprocess.check_output(
            [
                "git",
                "log",
                "--format=%aN",
                "--follow",
                "apertium-{0}.{0}.{1}".format(language, extension),
            ],
            cwd=REPOS_DIR.joinpath(dirName),
        ).decode("utf-8")

        if updatemailmap:
            commiters = (
                subprocess.check_output(
                    [
                        "git",
                        "log",
                        "--format=<%aE> %aN %cI %h",
                        "--follow",
                        "apertium-{0}.{0}.{1}".format(language, extension),
                    ],
                    cwd=REPOS_DIR.joinpath(dirName),
                )
                .decode("utf-8")
                .split("\n")
            )
            mailmap = open(
                SCRAPERS_DIR.joinpath(".mailmap"), "r", encoding="utf-8"
            ).read()
            for commiter in commiters:
                if not commiter.split(" ")[0] in mailmap:
                    print(commiter.encode("utf-8"), language)

        authors = lines.split("\n")
        authors.pop()  # last line is always empty
        contributors = []
        authorCount = Counter(authors)
        for contributor, count in authorCount.items():
            contributors.append({"user": contributor, "value": count})

        wikiURL = "http://wiki.apertium.org/wiki/" + langFamily + "_languages"
        wikiData = requests.get(wikiURL).text
        rows = etree.fromstring(
            wikiData, parser=etree.XMLParser(encoding="utf-8")
        ).find(
            ".//table[@class='wikitable sortable']"
        )  # The transducers table is always the first with this class

        stateCol = 6
        if langFamily == "celtic":  # Celtic's state cell is in a different column
            stateCol = 7

        for row in rows[2:]:  # ignores the header rows
            if rmPrefix(row[0][0][0].text) == language:  # name cell
                state = row[stateCol].text.strip()  # state cell
                break
            state = "unknown"

        data.append(
            {
                "lang": language,
                "state": state,
                "stems": stems,
                "location": "{} ({})".format(dirName, location),
                "contributors": contributors,
            }
        )

    return data


def pairData(packages, languages):
    """Returns the locations and stems of all specified pairs"""
    data = []
    for package in packages:
        if not re.match(r"apertium-\w+-\w+", package["name"]):
            continue

        pairName = rmPrefix(package["name"])
        pairSet = set(pairName.split("-"))
        if (
            not pairSet <= set(languages) or pairName == "ita-srd"
        ):  # This repo exists as srd-ita and ita-srd is empty
            continue
        for topic in package["topics"]:
            if rmPrefix(topic) in pairLocations:
                location = rmPrefix(topic)
                break

        try:
            stats = requests.get(
                "https://apertium.projectjj.com/stats-service/apertium-{}/bidix".format(
                    pairName
                )
            ).json()["stats"]
        except KeyError:
            raise Exception(
                "The stats-service seems to be updating at the moment. Please try again later"
            )
            # Raises an exception because the script can't continue

        for statistic in stats:
            if statistic["stat_kind"] == "Entries":
                stems = statistic["value"]
                break
        data.append({"langs": list(pairSet), "location": location, "stems": stems})

    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scrape data necessary for the visualizer of the specified family"
    )
    parser.add_argument(
        "-s",
        "--shallow",
        help="faster mode, doesn't dig through histories",
        action="store_true",
    )
    parser.add_argument(
        "-u",
        "--updatemailmap",
        help="outputs users that aren't on .mailmap",
        action="store_true",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        help="stop the script from printing status updates",
        action="store_true",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="log info about commits where the stems were unable to be counted",
        action="store_true",
    )
    parser.add_argument(
        "family", help="Family to scrape from",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.CRITICAL)
    # As this script already handles errors for the lexcccounter, disable logging for it:
    logging.getLogger("countStems").disabled = True

    family = args.family.lower()
    families = json.load(open(SCRAPERS_DIR.joinpath("families.json"), "r"))
    try:
        langs = families[family]
    except KeyError:
        raise Exception(
            "The family you specified is not in the families.json file.\nPlease choose another family or add the family to the file"
        )

    if not REPOS_DIR.exists():
        os.mkdir(REPOS_DIR)

    allPackages = requests.get(
        "https://apertium.projectjj.com/stats-service/packages"
    ).json()["packages"]
    pairsFile = open(
        JSON_DIR.joinpath("{}_pairData.json".format(family)), "w+", encoding="utf-8",
    )
    if not args.quiet:
        print(
            "Scraping pair data for {} languages...".format(family.capitalize()),
            flush=True,
        )
    json.dump(pairData(allPackages, langs), pairsFile, ensure_ascii=False)
    langsFile = open(
        JSON_DIR.joinpath("{}_transducers.json".format(family)), "w+", encoding="utf-8",
    )
    if not args.quiet:
        print(
            "Scraping monolingual data for {} languages...".format(family.capitalize()),
            flush=True,
        )
    json.dump(
        monoData(allPackages, langs, family, args.updatemailmap, args.quiet),
        langsFile,
        ensure_ascii=False,
    )
    if not args.shallow:
        for lang in langs:
            langHistory = []
            if not args.quiet:
                print(
                    "Getting commits for apertium-{}...".format(lang), flush=True,
                )
            langHistory.append(monoHistory(lang, args.quiet))
            langHistory.extend(pairHistory(lang, langs, allPackages, args.quiet))
            outputFile = open(
                JSON_DIR.joinpath("{}.json".format(lang)), "w+", encoding="utf-8",
            )
            json.dump(langHistory, outputFile, ensure_ascii=False)
    print("\nSuccesfully scraped data for {} languages!".format(family.capitalize()))

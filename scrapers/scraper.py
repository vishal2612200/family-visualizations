#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Usage: python <name>.py [-s] [-u]
   Output: Outputs data (necessary for the family visualizer) for languages in json files
   To change languages, change the languages, iso3to2 and family variables
"""

from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as etree
import argparse
import re
import logging
import json
import subprocess
import shutil
import requests

from lexccounter import countStems as countLexcStems
from dixcounter import get_info as countDixStems

SCRAPERS_DIR = Path(__file__).absolute().parent
ROOT_DIR = SCRAPERS_DIR.parent
REPOS_DIR = SCRAPERS_DIR.joinpath("git-repos")

languages = [
    "aze",
    "bak",
    "chv",
    "crh",
    "kaa",
    "kaz",
    "kir",
    "kjh",
    "kum",
    "nog",
    "sah",
    "tat",
    "tuk",
    "tur",
    "tyv",
    "uig",
    "uzb",
]
iso3to2 = {
    "aze": "az",
    "bak": "ba",
    "chv": "cv",
    "crh": "crh",
    "kaa": "kaa",
    "kaz": "kk",
    "kir": "ky",
    "kjh": "kjh",
    "kum": "kum",
    "nog": "nog",
    "sah": "sah",
    "tat": "tt",
    "tuk": "tk",
    "tyv": "tyv",
    "tur": "tr",
    "uig": "ug",
    "uzb": "uz",
}
pairLocations = ["incubator", "nursery", "staging", "trunk"]
langLocations = ["languages", "incubator"]
family = "Turkic"
wikiURL = "http://wiki.apertium.org/wiki/" + family + "_languages"


def rmPrefix(word):
    """Removes the apertium- prefix"""
    return word[len("apertium-") :]


def updateRepos():
    """Updates and cleans all repo dirs"""
    subprocess.call(
        ["git", "submodule", "update", "--init", "--recursive", "--quiet", "--force",],
        cwd=ROOT_DIR,
    )
    for repo in sorted(REPOS_DIR.glob("*")):
        subprocess.call(
            ["git", "clean", "-xfdf", "--quiet",], cwd=repo,
        )


def prepRepo(repo):
    """Adds repo if it doesn't exist and copies .mailmap to it"""
    if not REPOS_DIR.joinpath(repo).exists():
        subprocess.call(
            [
                "git",
                "submodule",
                "add",
                "--force",
                "--quiet",
                "https://github.com/apertium/{}".format(repo),
            ],
            cwd=REPOS_DIR,
        )
    shutil.copyfile(
        SCRAPERS_DIR.joinpath(".mailmap"), REPOS_DIR.joinpath(repo, ".mailmap"),
    )


def monoHistory(language):
    """Returns the history of a monolingual dictionary"""
    dirName = "apertium-{}".format(language)
    try:
        oldFile = json.load(
            open(ROOT_DIR.joinpath("json", "{}.json".format(language)), "r")
        )
        for data in oldFile:
            if data["name"] == language:
                history = data["history"]
                break
            history = []
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        history = []
    prepRepo(dirName)
    commits = (
        subprocess.check_output(
            [
                "git",
                "log",
                "--format=%H %aN %aI",
                "--follow",
                "apertium-{0}.{0}.lexc".format(language),
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
            "author": data[1],
            "date": data[2],
        }

        if any(commitData["sha"] == cm["sha"] for cm in history):
            continue

        lexcFile = requests.get(
            "https://raw.githubusercontent.com/apertium/apertium-{0}/{1}/apertium-{0}.{0}.lexc".format(
                language, commitData["sha"]
            )
        )
        if not lexcFile:
            lexcFile = requests.get(
                "https://raw.githubusercontent.com/apertium/apertium-{0}/{1}/apertium-{0}.{0}.lexc".format(
                    iso3to2[language], commitData["sha"]
                )
            )
        try:
            stems = countLexcStems(lexcFile.text)
        except SystemExit:
            logging.getLogger("monoHistory").warning(
                "Unable to count lexc stems for %s in commit %s",
                language,
                commitData["sha"],
            )
            continue

        commitData["stems"] = stems
        history.append(commitData)

    return {"name": language, "history": history}


def pairHistory(language, packages):
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
        if not set(pairList) <= set(languages):
            continue

        prepRepo(dirName)
        dixName = (
            pairName if pairName != "tat-kir" else "tt-ky"
        )  # The tat-kiz bidix is still named according to iso639-2 standards

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
                open(ROOT_DIR.joinpath("json", "{}.json".format(language)), "r")
            )
            for data in oldFile:
                if data["name"] == pairName:
                    history = data["history"]
                    break
                history = []
        except FileNotFoundError:
            history = []

        commits.pop()  # Last line is always empty
        for commit in commits:
            commitData = {}
            data = commit.split(" ")
            commitData["sha"] = data[0]
            commitData["author"] = data[1]
            commitData["date"] = data[2]

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


def monoData(packages, updatemailmap):
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
        stats = requests.get(
            "https://apertium.projectjj.com/stats-service/{}/Lexc".format(dirName)
        ).json()["stats"]
        for statistic in stats:
            if statistic["stat_kind"] == "Stems":
                stems = statistic["value"]
                break
        for topic in package["topics"]:
            if rmPrefix(topic) in langLocations:
                location = rmPrefix(topic)
                break

        prepRepo(dirName)
        lines = subprocess.check_output(
            [
                "git",
                "log",
                "--format=%aN",
                "--follow",
                "apertium-{0}.{0}.lexc".format(language),
            ],
            cwd=REPOS_DIR.joinpath(dirName),
        ).decode("utf-8")

        if updatemailmap:
            emails = (
                subprocess.check_output(
                    [
                        "git",
                        "log",
                        "--format=<%aE>",
                        "--follow",
                        "apertium-{0}.{0}.lexc".format(language),
                    ],
                    cwd=REPOS_DIR.joinpath(dirName),
                )
                .decode("utf-8")
                .split("\n")
            )
            mailmap = open(
                SCRAPERS_DIR.joinpath(".mailmap"), "r", encoding="utf-8"
            ).read()
            for email in emails:
                if not email in mailmap:
                    print(email)

        authors = lines.split("\n")
        authors.pop()  # last line is always empty
        contributors = []
        authorCount = Counter(authors)
        for contributor, count in authorCount.items():
            contributors.append({"user": contributor, "value": count})

        wikiData = requests.get(wikiURL).text
        rows = etree.fromstring(
            wikiData, parser=etree.XMLParser(encoding="utf-8")
        ).find(
            ".//table[@class='wikitable sortable']"
        )  # The transducers table is always the first with this class
        for row in rows[2:]:  # ignores the header rows
            if rmPrefix(row[0][0][0].text) == language:  # name cell
                state = row[6].text.strip()  # state cell
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


def pairData(packages):
    """Returns the locations and stems of all specified pairs"""
    data = []
    for package in packages:
        if not re.match(r"apertium-\w+-\w+", package["name"]):
            continue

        pairName = rmPrefix(package["name"])
        pairSet = set(pairName.split("-"))
        if not pairSet <= set(languages):
            continue
        for topic in package["topics"]:
            if rmPrefix(topic) in pairLocations:
                location = rmPrefix(topic)
                break
        stats = requests.get(
            "https://apertium.projectjj.com/stats-service/apertium-{}/bidix".format(
                pairName
            )
        ).json()["stats"]
        for statistic in stats:
            if statistic["stat_kind"] == "Entries":
                stems = statistic["value"]
                break
        data.append({"langs": list(pairSet), "location": location, "stems": stems})

    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape data for visualizer")
    parser.add_argument(
        "-s",
        "--shallow",
        help="Faster mode, doesn't dig through histories",
        action="store_true",
    )
    parser.add_argument(
        "-u",
        "--updatemailmap",
        help="outputs users that aren't on .mailmap",
        action="store_true",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Print info about commits where the stems were unable to be counted",
        action="store_true",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.CRITICAL)

    # As this script already handles errors for the lexcccounter, disable logging for it:
    logging.getLogger("countStems").disabled = True

    updateRepos()

    allPackages = requests.get(
        "https://apertium.projectjj.com/stats-service/packages"
    ).json()["packages"]
    pairsFile = open(ROOT_DIR.joinpath("json", "pairData.json"), "w+", encoding="utf-8")
    json.dump(pairData(allPackages), pairsFile, ensure_ascii=False)
    langsFile = open(
        ROOT_DIR.joinpath("json", "transducers.json"), "w+", encoding="utf-8"
    )
    json.dump(
        monoData(allPackages, args.updatemailmap), langsFile, ensure_ascii=False,
    )
    for lang in languages:
        if not args.shallow:
            langHistory = []
            langHistory.append(monoHistory(lang))
            langHistory.extend(pairHistory(lang, allPackages))
            outputFile = open(
                ROOT_DIR.joinpath("json", "{}.json".format(lang)),
                "w+",
                encoding="utf-8",
            )
            json.dump(langHistory, outputFile, ensure_ascii=False)
    updateRepos()  # Removes .mailmap from repos

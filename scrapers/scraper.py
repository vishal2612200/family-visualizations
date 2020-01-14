#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Usage: python <name>.py [-s] [-u] [-v ][-f FAMILY]
   Output: Outputs data (necessary for the family visualizer) for languages in FAMILY to json files
   Defaults to scraping Turkic languages, but can be changed with the -f argument
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

languages = []

families = {
    "turkic": [
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
    ],
    "romance": [
        "arg",
        "ast",
        "cat",
        "cos",
        "fra",
        "glg",
        "ita",
        "oci",
        "por",
        "ron",
        "rup",
        "scn",
        "spa",
        "srd",
    ],
    "germanic": [
        "afr",
        "dan",
        "deu",
        "eng",
        "fao",
        "isl",
        "nld",
        "nno",
        "nob",
        "sco",
        "swe",
        "yid",
    ],
    "slavic": [
        "hbs",
        "slv",
        "mkd",
        "ces",
        "rus",
        "bul",
        "pol",
        "ukr",
        "slk",
        "bel",
        "dsb",
        "hsb",
    ],
    "semitic": ["ara", "heb", "mlt",],
    "indic": ["ben", "hin", "mar", "san", "sin", "urd",],
    "celtic": ["bre", "cym", "gla", "gle", "glv",],
    "mongolic": ["bua", "khk",],
    "dravidian": ["mal", "tel",],
}
iso3to1 = {
    "aar": "aa",
    "abk": "ab",
    "afr": "af",
    "aka": "ak",
    "sqi": "sq",
    "amh": "am",
    "ara": "ar",
    "arg": "an",
    "hye": "hy",
    "asm": "as",
    "ast": "ast",
    "ava": "av",
    "ave": "ae",
    "aym": "ay",
    "aze": "az",
    "bak": "ba",
    "bam": "bm",
    "eus": "eu",
    "bel": "be",
    "ben": "bn",
    "bih": "bh",
    "bis": "bi",
    "bos": "bs",
    "bre": "br",
    "bul": "bg",
    "mya": "my",
    "cat": "ca",
    "cha": "ch",
    "che": "ce",
    "zho": "zh",
    "chu": "cu",
    "chv": "cv",
    "cor": "kw",
    "cos": "co",
    "cre": "cr",
    "crh": "crh",
    "ces": "cs",
    "dan": "da",
    "div": "dv",
    "nld": "nl",
    "dzo": "dz",
    "eng": "en",
    "epo": "eo",
    "est": "et",
    "ewe": "ee",
    "fao": "fo",
    "fij": "fj",
    "fin": "fi",
    "fra": "fr",
    "fry": "fy",
    "ful": "ff",
    "kat": "ka",
    "deu": "de",
    "gla": "gd",
    "gle": "ga",
    "glg": "gl",
    "glv": "gv",
    "ell": "el",
    "grn": "gn",
    "guj": "gu",
    "hat": "ht",
    "hau": "ha",
    "heb": "he",
    "her": "hz",
    "hin": "hi",
    "hmo": "ho",
    "hrv": "hr",
    "hun": "hu",
    "ibo": "ig",
    "isl": "is",
    "ido": "io",
    "iii": "ii",
    "iku": "iu",
    "ile": "ie",
    "ina": "ia",
    "ind": "id",
    "ipk": "ik",
    "ita": "it",
    "jav": "jv",
    "jpn": "ja",
    "kaa": "kaa",
    "kal": "kl",
    "kan": "kn",
    "kas": "ks",
    "kau": "kr",
    "kaz": "kk",
    "khm": "km",
    "kik": "ki",
    "kin": "rw",
    "kir": "ky",
    "kom": "kv",
    "kon": "kg",
    "kor": "ko",
    "kua": "kj",
    "kur": "ku",
    "lao": "lo",
    "lat": "la",
    "lav": "lv",
    "lim": "li",
    "lin": "ln",
    "lit": "lt",
    "ltz": "lb",
    "lub": "lu",
    "lug": "lg",
    "mkd": "mk",
    "mah": "mh",
    "mal": "ml",
    "mri": "mr",
    "mar": "mr",
    "msa": "ms",
    "mlg": "mg",
    "mlt": "mt",
    "mon": "mn",
    "nau": "na",
    "nav": "nv",
    "nbl": "nr",
    "nde": "nd",
    "ndo": "ng",
    "nep": "ne",
    "nno": "nn",
    "nob": "nb",
    "nor": "no",
    "nya": "ny",
    "oci": "oc",
    "oji": "oj",
    "ori": "or",
    "orm": "om",
    "oss": "os",
    "pan": "pa",
    "fas": "fa",
    "pli": "pi",
    "pol": "pl",
    "por": "pt",
    "pus": "ps",
    "que": "qu",
    "roh": "rm",
    "ron": "ro",
    "run": "rn",
    "rus": "ru",
    "sag": "sg",
    "sah": "sah",
    "san": "sa",
    "sin": "si",
    "hbs": "sh",
    "slk": "sk",
    "slv": "sl",
    "sme": "se",
    "smo": "sm",
    "sna": "sn",
    "snd": "sd",
    "som": "so",
    "sot": "st",
    "spa": "es",
    "srd": "sc",
    "srp": "sr",
    "ssw": "ss",
    "sun": "su",
    "swa": "sw",
    "swe": "sv",
    "tah": "ty",
    "tam": "ta",
    "tat": "tt",
    "tel": "te",
    "tgk": "tg",
    "tgl": "tl",
    "tha": "th",
    "bod": "bo",
    "tir": "ti",
    "ton": "to",
    "tsn": "tn",
    "tso": "ts",
    "tuk": "tk",
    "tur": "tr",
    "twi": "tw",
    "uig": "ug",
    "ukr": "uk",
    "urd": "ur",
    "uzb": "uz",
    "ven": "ve",
    "vie": "vi",
    "vol": "vo",
    "cym": "cy",
    "wln": "wa",
    "wol": "wo",
    "xho": "xh",
    "yid": "yi",
    "yor": "yo",
    "zha": "za",
    "zul": "zu",
    "kjh": "kjh",
    "kum": "kum",
    "nog": "nog",
    "tyv": "tyv",
    "scn": "scn",
    "rup": "rup",
    "sco": "sco",
    "hsb": "hsb",
    "dsb": "dsb",
    "bua": "bua",
    "khk": "khk",
}

pairLocations = ["incubator", "nursery", "staging", "trunk"]
langLocations = ["languages", "incubator"]


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
                iso3to1[language], commitData["sha"], extension
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
        if (
            not set(pairList) <= set(languages) or pairName == "ita-srd"
        ):  # This repo exists as srd-ita and ita-srd is empty
            continue

        prepRepo(dirName)
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
                open(ROOT_DIR.joinpath("json", "{}.json".format(language)), "r")
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
                dixName = iso3to1[pairList[0]] + "-" + iso3to1[pairList[1]]
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


def monoData(packages, langFamily, updatemailmap):
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
        prepRepo(dirName)
        extension = fileExt(language)
        if extension == "lexc":
            fileType = extension
        elif extension == "dix":  # extension is dix, but type is monodix
            fileType = "monodix"
        else:
            fileType = "metamonodix"  # extension is metadix, but type is metamonodix

        stats = requests.get(
            "https://apertium.projectjj.com/stats-service/{}/{}".format(
                dirName, fileType
            )
        ).json()["stats"]
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
                        "--format=<%aE> %aN %cI",
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


def pairData(packages):
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
    parser = argparse.ArgumentParser(
        description="Scrape data necessary for the visualizer of a family, defaulting to scraping for Turkic languages"
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
    languages = families[family]

    updateRepos()

    allPackages = requests.get(
        "https://apertium.projectjj.com/stats-service/packages"
    ).json()["packages"]
    pairsFile = open(
        ROOT_DIR.joinpath("json", "{}_pairData.json".format(family)),
        "w+",
        encoding="utf-8",
    )
    json.dump(pairData(allPackages), pairsFile, ensure_ascii=False)
    langsFile = open(
        ROOT_DIR.joinpath("json", "{}_transducers.json".format(family)),
        "w+",
        encoding="utf-8",
    )
    json.dump(
        monoData(allPackages, family, args.updatemailmap),
        langsFile,
        ensure_ascii=False,
    )
    if not args.shallow:
        for lang in languages:
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

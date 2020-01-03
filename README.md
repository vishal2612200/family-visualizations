# Family Visualizations

TODO: Add content

## Updating the data

The data for the family visualizer is contained in `.json` files within the `json/` folder. This data can be automatically updated using the `scraper.py` script located in the `scrapers/` folder.

By default, the script gets the history of all languages and pairs, as well as some other data used by the visualizer, for languages in the `languages` list, but it can also be run in "shallow" mode (`-s` or `--shallow`) to only get data for the `pairData.json` and `transducers.json` files, while the normal mode updates all `{lang}.json` files as well. (To change the languages scraped, make sure to also change the `iso3to2` and `family` variables).

To count contributions properly, the script uses a `.mailmap` file, to avoid commits made by the same person but under different names/emails being counted separately (e.g. commits by "John Doe" and by "J. Doe" would be counted separately). To update this file, the script has an "update mailmap" mode (`-u` or `--updatemailmap`) that outputs the emails that aren't on the `.mailmap` file (they must then be added manually, as the script can't figure out whether or not this committer is already in the file, but with a different email) There is no need to use this option without shallow mode, as it only logs committers that would go in `transducers.json`, since the contributions are only counted in this file.

Because of an issue with the GitHub API not working well with file renames, the script uses submodules for each language (located in the `scrapers/git-repos/` folder) and pair and gets the data by running `git log` in it, which is slow, but there is no other option to get the full history of a pair. To avoid being slower than necessary, the scraper ignores commits that are already in the files and only gets data for the ones that aren't. This scraper should be updated if either the GH API is updated to support history past file renames or if [the stats-service](https://github.com/apertium/apertium-stats-service/) is updated to support history (see [this issue](https://github.com/apertium/apertium-stats-service/issues/46)).

Notes:
- Some commits are skipped because their stems can't be counted (because of a syntax error in the dictionary, in most cases). To print some info about these, use `-v` or `--verbose`.
- If run on Windows, `git` will give such errors: `error: unable to create file tests/morphotactics/prefixes/PRN.*: No such file or directory` and then `Unable to checkout '*' in submodule path 'scrapers/git-repos/apertium-*'`. This causes no issues for the script and is due to [this issue](https://github.com/apertium/organisation/issues/11)
- The scripts contained within the `scrapers/svn-old` folder are the old scrapers that got the data from the svn repo. They shouldn't be run anymore.

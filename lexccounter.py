#!/usr/bin/env python3

import argparse, re, sys, urllib.request, logging, itertools
from collections import defaultdict

def cleanLine(line):
    return re.sub(r'!.*$', '', re.sub(r'%(.)', r'\1', line.strip())).strip()

def countStems(dictionary, uniqueOn='lemma+continuationLexicon'):
    logger = logging.getLogger("countStems")
    currentLexicon = None
    lexicons = defaultdict(lambda: ([], set()))

    if uniqueOn not in {'lemma+continuationLexicon', 'lemma+gloss', 'lemma+comment'}:
        raise ValueError('invalid unique criteria: ' + uniqueOn)

    for lineNo, line in enumerate(dictionary.splitlines()):
        line = cleanLine(line)
        if line.startswith('LEXICON'):
            logger.info('Switching lexicon from %s (%s unique entries, %s pointers) to %s' % (currentLexicon, len(lexicons[currentLexicon][1]), len(lexicons[currentLexicon][0]), line.split()[1]))
            currentLexicon = line.split()[1]
        elif not line.startswith('!') and line and currentLexicon:
            try:
                if len(re.findall(r'\s+', line)) >= 2:
                    if ':' in line:
                        split = re.findall(r'^(.+?):([^;]+);(?:\s+!\s+(.+))?', line)
                        if len(split):
                            split = split[0]
                            lemma = split[0].strip()
                            continuationLexicon = split[1].strip().split()[-1].split('-')
                            gloss = split[2].strip()
                            if uniqueOn == 'lemma+continuationLexicon':
                                lexicons[currentLexicon][1].add((lemma, frozenset(continuationLexicon)))
                            elif uniqueOn == 'lemma+gloss' or uniqueOn == 'lemma+comment':
                                lexicons[currentLexicon][1].add((lemma, gloss))
                            logger.debug('Parsed L%s (%s) as lemma: %s, continuations: %s, and gloss: %s' % (lineNo + 1, line, repr(lemma), repr(continuationLexicon), repr(gloss)))
                        else:
                            logger.warning('Failed to parse L%s: %s' % (lineNo + 1, line))
                    else:
                        split = line.split(';')[0].strip().split()
                        lemma = split[0]
                        continuationLexicon = split[1].strip().split('-')
                        gloss = line.split('!')[1].strip() if '!' in line else None
                        if uniqueOn == 'lemma+continuationLexicon':
                            lexicons[currentLexicon][1].add((lemma, frozenset(continuationLexicon)))
                        elif uniqueOn == 'lemma+gloss' or uniqueOn == 'lemma+comment':
                            lexicons[currentLexicon][1].add((lemma, frozenset(continuationLexicon)))

                        logger.debug('Parsed L%s (%s) as lemma: %s, continuations: %s, and gloss: %s' % (lineNo + 1, line, repr(lemma), repr(continuationLexicon), repr(gloss)))
                elif len(re.findall(r'\s+', line)) == 1:
                    lexiconPointer = line.split(';')[0].strip()
                    if ' ' in lexiconPointer:
                        logger.warning('Failed to parse L%s: %s' % (lineNo + 1, line))
                    else:
                        lexicons[currentLexicon][0].append(lexiconPointer)
                else:
                    logger.warning('Failed to parse L%s: %s' % (lineNo + 1, line))
            except Exception as e:
                logger.warning('Failed to parse L%s: %s' % (lineNo + 1, line))
    logger.info('Switching lexicon from %s (%s unique entries, %s pointers) to %s' % (currentLexicon, len(lexicons[currentLexicon][1]), len(lexicons[currentLexicon][0]), 'END'))

    def getAllLexicons(rootLexicon):
        return lexicons[rootLexicon][0] + sum(map(getAllLexicons, lexicons[rootLexicon][0]), [])

    if 'Root' in lexicons:
        validLexicons = set(getAllLexicons('Root'))
        logger.info('Counting from lexicons %s' % validLexicons)
    else:
        logger.critical('No Root lexicon found')
        sys.exit(-1)

    entries = set()
    for validLexicon in validLexicons:
        logging.info('In lexicon %s referenced from ROOT, found %s entries.' % (validLexicon, len(lexicons[validLexicon][1])))
        entries.update(lexicons[validLexicon][1])

    print('Unique entries: %s' % len(entries))
    return len(entries)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Count unique stems (on lemma and continuation lexicon) in a HFST morphological dictionary (lexc)")
    parser.add_argument('uri', help="uri to lexc file")
    parser.add_argument('-l', '--uniqLemmaGloss', help="count stems unique on lemma and gloss (comment)", action='store_true', default=False)
    parser.add_argument('-v', '--verbose', help="show errors dictionary (verbose)", action='store_true', default=False)
    parser.add_argument('-vv', '--doubleVerbose', help="show progress through dictionary (verbose×2)", action='store_true', default=False)
    parser.add_argument('-vvv', '--tripleVerbose', help="show detailed progress through dictionary (verbose×3)", action='store_true', default=False)
    args = parser.parse_args()

    if args.tripleVerbose:
        logging.basicConfig(level=logging.DEBUG)
    elif args.doubleVerbose:
        logging.basicConfig(level=logging.INFO)
    elif args.verbose:
        logging.basicConfig(level=logging.WARNING)
    else:
        logging.basicConfig(level=logging.ERROR)

    if 'http' in args.uri:
        try:
            dictionary = str((urllib.request.urlopen(args.uri)).read(), 'utf-8')
        except urllib.error.HTTPError:
            logging.critical('Dictionary %s not found' % args.uri)
            sys.exit(-1)

        if args.uniqLemmaGloss:
            countStems(dictionary, uniqueOn='lemma+gloss')
        else:
            countStems(dictionary)
    else:
        try:
            with open(args.uri) as dictionary:
                if args.uniqLemmaGloss:
                    countStems(dictionary.read(), uniqueOn='lemma+gloss')
                else:
                    countStems(dictionary.read())
        except FileNotFoundError:
            logging.critical('Dictionary %s not found' % args.uri)
            sys.exit(-1)

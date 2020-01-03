#!/usr/bin/env python3
'''Usage: python3 <name>.py dict_url
   Output: prints number of stems in that dict.

   Issues: If dict encoding is not convertable to utf-8, returns -1
'''
import sys, urllib.request, logging
import xml.etree.ElementTree as xml
import argparse, urllib.request

def print_info(uri, bidix=None):
    returned = get_info(uri, bidix)
    if "stems" in returned:
        print('Stems: %s' % returned['stems'])
    if "paradigms" in returned:
        print('Paradigms: %s' % returned['paradigms'])

def get_info(uri, bidix=None):
    dictX = ""
    if "http" in uri:
        try:
            dictX = str((urllib.request.urlopen(uri)).read(), 'utf-8')
        except:
            return -1 # FIXME: error handling

    else:
        dictX = (open(uri, 'r')).read()
    try:
        tree = xml.fromstring(dictX)
    except:
        return -1  # FIXME: error handling

    if bidix is not None:
        bi = bidix
    else:
        bi = len(tree.findall("pardefs")) == 0 #bilingual dicts don't have pardefs section -- not necessarily true? check /trunk/apertium-en-es/apertium-en-es.en-es.dix

    bi = True
    out = {}
    if(bi):
        out['stems'] = len(tree.findall("*[@id='main']/e//l"))
        #print('Stems: %s ' % len(tree.findall("*[@id='main']/e//l")))
    else:
        #print('Stems: %s' % len(tree.findall("section/*[@lm]")))  # there can be sections other than id="main"
        out['stems'] = len(tree.findall("section/*[@lm]"))  # there can be sections other than id="main"
        if tree.find('pardefs') is not None:
            #print('Paradigms: %s' % len(tree.find('pardefs').findall("pardef")))
            out['paradigms'] = len(tree.find('pardefs').findall("pardef"))
    return out

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Count unique stems in a monolingual or bilingual dictionary (lttoolbox dix format)")
    parser.add_argument('-b', '--bidix', help="forces counter to assume bidix", action='store_true', default=False)
    parser.add_argument('uri', help="uri to a dix file")
    args = parser.parse_args()

    #uri = sys.argv[1]
    if 'http' in args.uri:
        try:
            if args.bidix:
                print_info(args.uri, bidix=True)
            else:
                print_info(args.uri)
        except urllib.error.HTTPError:
            logging.critical('Dictionary %s not found' % args.uri)
            sys.exit(-1)
    else:
        if args.bidix:
            print_info(args.uri, bidix=True)
        print_info(args.uri)

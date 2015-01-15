#!/usr/bin/env ruby

require 'nokogiri'
require 'json'

location, lang, outputfile = ARGV
filename = "https://svn.code.sf.net/p/apertium/svn/#{location}/apertium-#{lang}/apertium-#{lang}.#{lang}.lexc"
log = `svn log --xml #{filename}`
doc = Nokogiri::XML(log)

if outputfile && File.exist?(outputfile)
    stems = JSON.parse(File.read(outputfile))
    revs = stems.map { |entry| entry['rev'] }
else
    stems = []
    revs = []
end

added, skipped = 0, 0

doc.css("logentry").each do |logentry|
    rev = logentry.attr("revision").to_i
    if revs.include?(rev)
        skipped += 1
    else
        out = `svn export #{filename} /tmp/#{lang}.#{rev}.lexc --force -r #{rev} 2>&1`
        stems << {
            'rev' => rev,
            'stems' => `python3 ./lexccounter.py /tmp/#{lang}.#{rev}.lexc`.split(" ")[2].chomp.to_i,
            'author' => logentry.css('author')[0].content,
            'date' => logentry.css('date')[0].content
        }
        `rm /tmp/#{lang}.#{rev}.lexc`
        added += 1
    end
    #puts stems.to_json
end

if added > 0
    if outputfile
        File.write(outputfile, stems.to_json)
    else
        puts stems.to_json
    end
end

puts "Added #{added} and skipped #{skipped} (already existing) revisions."



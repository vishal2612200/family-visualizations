#!/usr/bin/env ruby

require 'nokogiri'
require 'json'

location, lang, format, outputfile = ARGV
filename = "https://svn.code.sf.net/p/apertium/svn/#{location}/apertium-#{lang}/apertium-#{lang}.#{lang}.#{format}"
log = `svn log --xml #{filename}`
doc = Nokogiri::XML(log)

if outputfile && File.exist?(outputfile)
    all = JSON.parse(File.read(outputfile))
    if all && all.any? { |e| e['name'] == lang }
        stems = (all.select { |e| e['name'] == lang })[0]['history']
        revs = stems.map { |entry| entry['rev'] }
    else
        stems = []
        revs = []
    end
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
        out = `svn export #{filename} /tmp/#{lang}.#{rev}.#{format} --force -r #{rev} 2>&1`
        if format == 'lexc'
            num = `python3 ./lexccounter.py /tmp/#{lang}.#{rev}.lexc`.split(" ")[2].chomp.to_i
        else
            num = Nokogiri::XML(File.open("/tmp/#{lang}.#{rev}.dix")).xpath("descendant-or-self::*[@id = 'main']/descendant::e/descendant::l").length
        end
        stems << {
            :rev => rev,
            :stems => num,
            :author => logentry.css('author')[0].content,
            :date => logentry.css('date')[0].content
        }
        `rm /tmp/#{lang}.#{rev}.#{format}`
        added += 1
    end
    #puts stems.to_json
end

if added > 0
    if outputfile
        all = JSON.parse(File.read(outputfile))
        if all
            all = all.keep_if {|e| e['name'] != lang }
            all << {:name => lang, :history => stems}
            File.write(outputfile, all.to_json)
        else
            File.write(outputfile, [{:name => lang, :history => stems}].to_json)
        end
    else
        puts stems.to_json
    end
end

puts "Added #{added} and skipped #{skipped} (already existing) revisions."

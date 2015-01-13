#!/usr/bin/env ruby

require 'nokogiri'
require 'json'

location, lang = ARGV
filename = "https://svn.code.sf.net/p/apertium/svn/#{location}/apertium-#{lang}/apertium-#{lang}.#{lang}.lexc"
log = `svn log --xml #{filename}`
doc = Nokogiri::XML(log)

begin
    stems = []
    doc.css("logentry").each do |logentry|
        rev = logentry.attr("revision").to_i
        out = `svn export #{filename}@#{rev} /tmp/#{lang}.#{rev}.lexc --force 2>&1`
        if not out.include? "Export complete."
            location = "incubator"
            filename = "https://svn.code.sf.net/p/apertium/svn/#{location}/apertium-#{lang}/apertium-#{lang}.#{lang}.lexc"
            `svn export #{filename}@#{rev} /tmp/#{lang}.#{rev}.lexc --force 2>&1`
        end
        stems << {
            'rev' => rev,
            'stems' => `python3 ./lexccounter.py /tmp/#{lang}.#{rev}.lexc`.split(" ")[2].chomp.to_i,
            'author' => logentry.css('author')[0].content,
            'date' => logentry.css('date')[0].content
        }
        `rm /tmp/#{lang}.#{rev}.lexc`
        #puts stems.to_json
    end
rescue
    puts stems.to_json
end

puts stems.to_json

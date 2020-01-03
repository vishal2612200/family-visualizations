#!/usr/bin/env ruby

xml = `svn log --xml https://svn.code.sf.net/p/apertium/svn/#{ARGV[0]}/apertium-#{ARGV[1]}`
require 'nokogiri'
doc = Nokogiri::XML(xml); nil
authors = Hash.new(0)
doc.xpath("//author").each { |author| authors[author.text] += 1 }
require 'json'
puts (authors.to_a.map { |author| { :user => author[0], :value => author[1]} }).to_json

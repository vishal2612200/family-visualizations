languages=( sah uig crh tyv aze chv tat tur kum kaa uzb bak nog tuk kaz alt cjs krc nog gag )
for lang in "${languages[@]}"
do
  ruby overtime.rb incubator $lang lexc ./json/$lang.json
done

<!-- instructions.md --> -->

Now, to continue our script ...

The front matter of the file needs to pull in data from the frontmatter.yml file, such that (template.tex => frontmatter.yml value of the given key in column 'yaml file'):

| Tex file     | yaml file               |
|--------------|-----------------------|
|TITLE         |title|
|AUTHOR|author|
|PUBLICATION_DATE|original_publication -> date|
|ISBN|isbn|

You already nailed adding in the Table of Contents!
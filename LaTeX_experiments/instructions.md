<!-- instructions.md --> -->

I'm trying to automate the process of importing text into a Latex template file. The raw text is in markdown format, each chapter in an individual file in a subfolder called /chapters. 

Also in this folder is a file called frontmatter.yml that contains metadata about the chapters, including the book title, author, etc. This will be used to populate other parts of the template. We'll detail that later.

For now, I want to create a python script that will take each chapter, including the number, title, and body, and parse it so that it can be inserted into the .tex template. The .tex file will then be saved as the TITLE.tex, from the yaml file.

In template.tex, I have the following code snippet:

`
\begin{ChapterStart}
\vspace{3\nbs}
\ChapterSubtitle[l]{Chapter CHAPTER_NUM}
\ChapterTitle[l]{CHAPTER_NAME}
\end{ChapterStart}
\FirstLine{\noindent CHAPTER_BODY

\vspace{2\nbs}
\ChapterDeco[c1]{\decoglyph{e9665}}
\clearpage
\thispagestyle{empty}
`

I want the script to loop through the individual markdown files in the folder /chapters and copy the content for that chapter into this template such that:

| Tex file     | Md file               |
|--------------|-----------------------|
|CHAPTER_NUM   |### Chapter 1 (just the numeral)|
|CHAPTER_NAME  |## Returning Home|
|CHAPTER_BODY  |the rest of the file|

The script will read ch1.md and find/replace the all caps placeholder text with the actual text from the markdown file. Then repeat the same process for ch2.md and putting it below the previous chapter; and repeat for each chapter in the /chapter folder.

And abbreviated example of the final .tex file from a couple shortened markdown files would be:

ch1.md ->

### Chapter 1

## A Random Chapter Title

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vivamus malesuada fringilla eros, nec fermentum enim cursus ac. Phasellus euismod turpis ut justo sagittis, vel blandit nunc scelerisque. Sed id justo ac nisi hendrerit dignissim. Nullam a justo et arcu ultricies posuere sit amet eget orci. Vestibulum et velit vitae arcu faucibus fermentum. Mauris venenatis semper orci, at tincidunt orci suscipit ac. Cras ut nisi a nunc ultricies euismod non nec velit.

Ut in massa ut nunc varius convallis id a nulla. Nam vehicula cursus turpis, vitae sodales est ullamcorper id. Integer consectetur lectus id vehicula fringilla. Quisque auctor leo at semper fringilla. Phasellus faucibus felis sed justo elementum, a tincidunt velit luctus. In dignissim, arcu et venenatis pharetra, nunc odio facilisis lorem, id tincidunt est odio et magna. Nullam scelerisque velit et mauris suscipit vestibulum.

Pellentesque lacinia felis eu magna consequat, ut luctus turpis facilisis. Curabitur ac metus id erat luctus consectetur. Aliquam vitae velit ut risus feugiat congue. Sed vestibulum orci sit amet turpis elementum tincidunt. Aliquam volutpat felis ut urna consequat, eget finibus justo ultrices. Nam et erat ut lacus aliquet elementum. Integer luctus neque sit amet purus consequat, vel hendrerit urna malesuada. Morbi sed ante at mauris ultricies varius non sit amet velit.

ch2.md ->

### Chapter 2

## A Different One

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nullam vel vehicula nunc. Ut rhoncus, arcu sed malesuada auctor, ipsum erat sollicitudin enim, vitae fermentum sapien erat a nulla. Quisque id turpis ac justo gravida cursus. Proin id magna nec nisl lacinia auctor. Duis auctor libero vel diam suscipit, ac pharetra lacus euismod. Sed suscipit tellus eu justo tincidunt, non commodo sapien sagittis. Integer et nulla ac orci vehicula hendrerit at a sapien. Aenean sit amet purus non sem aliquam malesuada.

Sed eget ex at orci dictum sagittis. Vestibulum bibendum arcu a mi consequat, nec accumsan nisi gravida. Nulla vel lacinia arcu, at vulputate est. Nam eu lectus at augue laoreet tincidunt. Suspendisse scelerisque interdum odio, ut dictum metus dapibus nec. Vivamus pharetra mauris non dignissim gravida. Donec suscipit, metus vitae varius vestibulum, ipsum odio feugiat velit, nec hendrerit lectus sapien nec lorem. Aliquam erat volutpat. Nam tincidunt turpis ac nunc congue, non aliquam odio scelerisque.

Maecenas euismod diam sit amet risus placerat, sed efficitur dolor vestibulum. Ut blandit justo non nisi venenatis, nec bibendum mauris gravida. Proin sit amet consectetur enim, sed venenatis sapien. Morbi et dictum augue. Sed ultricies tellus nec justo vulputate, in eleifend enim hendrerit. Aenean a fringilla odio, sed convallis velit. Vivamus non dignissim mi, vel fringilla ligula. Etiam aliquet nisi nec felis bibendum feugiat. Phasellus vel lectus a ex bibendum scelerisque.

tex file that is created ->

\begin{ChapterStart}
\vspace{3\nbs}
\ChapterSubtitle[l]{Chapter 1}
\ChapterTitle[l]{A Random Chapter Title}
\end{ChapterStart}
\FirstLine{\noindent Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vivamus malesuada fringilla eros, nec fermentum enim cursus ac. Phasellus euismod turpis ut justo sagittis, vel blandit nunc scelerisque. Sed id justo ac nisi hendrerit dignissim. Nullam a justo et arcu ultricies posuere sit amet eget orci. Vestibulum et velit vitae arcu faucibus fermentum. Mauris venenatis semper orci, at tincidunt orci suscipit ac. Cras ut nisi a nunc ultricies euismod non nec velit.}

Ut in massa ut nunc varius convallis id a nulla. Nam vehicula cursus turpis, vitae sodales est ullamcorper id. Integer consectetur lectus id vehicula fringilla. Quisque auctor leo at semper fringilla. Phasellus faucibus felis sed justo elementum, a tincidunt velit luctus. In dignissim, arcu et venenatis pharetra, nunc odio facilisis lorem, id tincidunt est odio et magna. Nullam scelerisque velit et mauris suscipit vestibulum.

Pellentesque lacinia felis eu magna consequat, ut luctus turpis facilisis. Curabitur ac metus id erat luctus consectetur. Aliquam vitae velit ut risus feugiat congue. Sed vestibulum orci sit amet turpis elementum tincidunt. Aliquam volutpat felis ut urna consequat, eget finibus justo ultrices. Nam et erat ut lacus aliquet elementum. Integer luctus neque sit amet purus consequat, vel hendrerit urna malesuada. Morbi sed ante at mauris ultricies varius non sit amet velit.

\vspace{2\nbs}
\ChapterDeco[c1]{\decoglyph{e9665}}
\clearpage
\thispagestyle{empty}

\begin{ChapterStart}
\vspace{3\nbs}
\ChapterSubtitle[l]{Chapter 2}
\ChapterTitle[l]{A Different One}
\end{ChapterStart}
\FirstLine{\noindent Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nullam vel vehicula nunc. Ut rhoncus, arcu sed malesuada auctor, ipsum erat sollicitudin enim, vitae fermentum sapien erat a nulla. Quisque id turpis ac justo gravida cursus. Proin id magna nec nisl lacinia auctor. Duis auctor libero vel diam suscipit, ac pharetra lacus euismod. Sed suscipit tellus eu justo tincidunt, non commodo sapien sagittis. Integer et nulla ac orci vehicula hendrerit at a sapien. Aenean sit amet purus non sem aliquam malesuada.}

Sed eget ex at orci dictum sagittis. Vestibulum bibendum arcu a mi consequat, nec accumsan nisi gravida. Nulla vel lacinia arcu, at vulputate est. Nam eu lectus at augue laoreet tincidunt. Suspendisse scelerisque interdum odio, ut dictum metus dapibus nec. Vivamus pharetra mauris non dignissim gravida. Donec suscipit, metus vitae varius vestibulum, ipsum odio feugiat velit, nec hendrerit lectus sapien nec lorem. Aliquam erat volutpat. Nam tincidunt turpis ac nunc congue, non aliquam odio scelerisque.

Maecenas euismod diam sit amet risus placerat, sed efficitur dolor vestibulum. Ut blandit justo non nisi venenatis, nec bibendum mauris gravida. Proin sit amet consectetur enim, sed venenatis sapien. Morbi et dictum augue. Sed ultricies tellus nec justo vulputate, in eleifend enim hendrerit. Aenean a fringilla odio, sed convallis velit. Vivamus non dignissim mi, vel fringilla ligula. Etiam aliquet nisi nec felis bibendum feugiat. Phasellus vel lectus a ex bibendum scelerisque.

\vspace{2\nbs}
\ChapterDeco[c1]{\decoglyph{e9665}}
\clearpage
\thispagestyle{empty}


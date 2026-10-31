SP ?= /tmp/jozve-build

.PHONY: all pdf web clean pages

all: pdf web

pdf:
	cd src && xelatex -interaction=nonstopmode -halt-on-error main.tex >/dev/null && xelatex -interaction=nonstopmode -halt-on-error main.tex >/dev/null
	cp src/main.pdf Jozve-Automata.pdf

web:
	cd web && npm install --no-audit --no-fund >/dev/null
	python3 web/build.py docs

clean:
	rm -f src/*.aux src/*.log src/*.out src/*.toc src/main.pdf
	rm -rf web/build

pages: web
	git subtree split --prefix docs -b gh-pages-tmp
	git push -f origin gh-pages-tmp:gh-pages
	git branch -D gh-pages-tmp

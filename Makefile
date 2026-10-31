SP ?= /tmp/jozve-build

.PHONY: all pdf web clean

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

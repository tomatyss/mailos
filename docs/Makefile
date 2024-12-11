# Minimal makefile for Sphinx documentation

SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build
PORT          = 8001

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile clean dev livehtml

clean:
	rm -rf $(BUILDDIR)/*

# Development server with auto-reload
dev:
	sphinx-autobuild \
		--port $(PORT) \
		--open-browser \
		--watch $(SOURCEDIR) \
		--watch ../src/mailos \
		--re-ignore ".*\.pyc$$" \
		--re-ignore ".*\.git/.*" \
		--re-ignore ".*\.pytest_cache/.*" \
		--re-ignore ".*/__pycache__/.*" \
		"$(SOURCEDIR)" "$(BUILDDIR)/html" $(SPHINXOPTS) $(O)

# Legacy target for compatibility
livehtml: dev

# Default build target
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

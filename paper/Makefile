freshness_contracts.pdf: freshness_contracts.tex freshness_references.bib IEEEtran.cls IEEEtran.bst \
  freshness_summary.tex freshness_latency_table.tex freshness_trace_caption.tex freshness_sensitivity_table.tex \
  $(wildcard figures/*.pdf)
	pdflatex -interaction=nonstopmode -halt-on-error freshness_contracts.tex
	bibtex freshness_contracts
	pdflatex -interaction=nonstopmode -halt-on-error freshness_contracts.tex
	pdflatex -interaction=nonstopmode -halt-on-error freshness_contracts.tex

clean:
	rm -f *.aux *.bbl *.blg *.log *.out freshness_contracts.pdf

.PHONY: clean

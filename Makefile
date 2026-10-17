.PHONY: help install test lint demo clean

help:
	@echo "make install   install ShieldLint (editable)"
	@echo "make test      run the full test-suite (70 tests)"
	@echo "make lint      lint ShieldLint's own source"
	@echo "make demo      lint the deliberately leaky example"

install:
	python -m pip install -e .

test:
	python -m unittest discover -s tests -t . -v

lint:
	python -m shieldlint check shieldlint --no-color

demo:
	-python -m shieldlint check examples/vulnerable-checkout --no-color

clean:
	rm -rf build dist *.egg-info **/__pycache__

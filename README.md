# personality_questionnaire
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![python](https://img.shields.io/badge/Python-3.11-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://www.mypy-lang.org/)

Personality and general questionnaire processing methods for various experiments.

# Supported Questionnaires
* BFI-2
* VAS-F

## Inputs
Questionnaire answers are...
* read via command line interface
* ints in a numpy ndarray (.npy)
* ints in a csv file (.csv)
* strings in a csv file (.csv)

## Outputs
For BFI-2, the OCEAN and FACET values are scaled to the range [0..1] per participant.

For VAS-F, the relative values are calculated.

# Setup
### Install package from PyPI
```
pip install personality_questionnaire
```

### Install package for development
```
git clone https://github.com/fodorad/personality_questionnaire
cd personality_questionnaire
pip install .
pip install -U -r requirements.txt
python -m unittest discover -s test
```

# Quick start
## Run interactive BFI-2 questionnaire
```
python personality_questionnaire/api.py --participant_id test --questionnaire bfi2
```

## Run interactive VAS-F (pre- and post-)questionnaires
```
python personality_questionnaire/api.py --participant_id test --questionnaire vasf --vasf_tag pre
python personality_questionnaire/api.py --participant_id test --questionnaire vasf --vasf_tag post
```

# Projects using exordium

### (2022) PersonalityLinMulT
LinMulT is trained for Big Five personality trait estimation using the First Impressions V2 dataset and sentiment estimation using the MOSI and MOSEI datasets.
* paper: Multimodal Sentiment and Personality Perception Under Speech: A Comparison of Transformer-based Architectures ([pdf](https://proceedings.mlr.press/v173/fodor22a/fodor22a.pdf), [website](https://proceedings.mlr.press/v173/fodor22a.html))
* code: https://github.com/fodorad/PersonalityLinMulT

# What's next
* Add support for the following questionnaires: HEXACO

# Updates
* 1.1.0: Add support for VAS-F and interactive CMD interface.
* 1.0.0: Add support for BFI-2 and PyPI publish.

# Contact
* Ádám Fodor (foauaai@inf.elte.hu)
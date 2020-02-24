import json
import tempfile
from typing import Text

import pytest

import rasa.utils.io
from rasa.nlu import config, load_data
from rasa.nlu.components import ComponentBuilder, validate_required_components_from_data
from rasa.nlu.registry import registered_pipeline_templates
from tests.nlu.conftest import CONFIG_DEFAULTS_PATH, DEFAULT_DATA_PATH
from tests.nlu.utilities import write_file_config
from rasa.nlu.model import Trainer

defaults = rasa.utils.io.read_config_file(CONFIG_DEFAULTS_PATH)


def test_default_config(default_config):
    assert default_config.as_dict() == defaults


def test_blank_config():
    file_config = {}
    f = write_file_config(file_config)
    final_config = config.load(f.name)
    assert final_config.as_dict() == defaults


def test_invalid_config_json():
    file_config = """pipeline: [pretrained_embeddings_spacy"""  # invalid yaml
    with tempfile.NamedTemporaryFile("w+", suffix="_tmp_config_file.json") as f:
        f.write(file_config)
        f.flush()
        with pytest.raises(config.InvalidConfigError):
            config.load(f.name)


def test_invalid_pipeline_template():
    args = {"pipeline": "my_made_up_name"}
    f = write_file_config(args)
    with pytest.raises(config.InvalidConfigError) as execinfo:
        config.load(f.name)
    assert "unknown pipeline template" in str(execinfo.value)


@pytest.mark.parametrize(
    "pipeline_template", list(registered_pipeline_templates.keys())
)
def test_pipeline_registry_lookup(pipeline_template: Text):
    args = {"pipeline": pipeline_template}
    f = write_file_config(args)
    final_config = config.load(f.name)
    components = [c for c in final_config.pipeline]

    assert json.dumps(components, sort_keys=True) == json.dumps(
        registered_pipeline_templates[pipeline_template], sort_keys=True
    )


def test_default_config_file():
    final_config = config.RasaNLUModelConfig()
    assert len(final_config) > 1


def test_set_attr_on_component():
    cfg = config.load("sample_configs/config_pretrained_embeddings_spacy.yml")
    cfg.set_component_attr(6, C=324)

    assert cfg.for_component(1) == {"name": "SpacyTokenizer"}
    assert cfg.for_component(6) == {"name": "SklearnIntentClassifier", "C": 324}


def test_override_defaults_supervised_embeddings_pipeline():
    cfg = config.load("data/test/config_embedding_test.yml")
    builder = ComponentBuilder()

    component1_cfg = cfg.for_component(0)

    component1 = builder.create_component(component1_cfg, cfg)
    assert component1.max_ngram == 3

    component2_cfg = cfg.for_component(1)
    component2 = builder.create_component(component2_cfg, cfg)
    assert component2.epochs == 10


def test_warn_no_pretrained_extractor():
    cfg = config.load("sample_configs/config_spacy_entity_extractor.yml")
    trainer = Trainer(cfg)
    training_data = load_data(DEFAULT_DATA_PATH)
    with pytest.warns(UserWarning) as record:
        validate_required_components_from_data(trainer.pipeline, training_data)

    assert len(record) == 1


def test_warn_missing_regex_featurizer():
    cfg = config.load("sample_configs/config_crf_no_regex.yml")
    trainer = Trainer(cfg)
    training_data = load_data(DEFAULT_DATA_PATH)
    with pytest.warns(UserWarning) as record:
        validate_required_components_from_data(trainer.pipeline, training_data)

    assert len(record) == 1


def test_warn_missing_pattern_feature_lookup_tables():
    cfg = config.load("sample_configs/config_crf_no_pattern_feature.yml")
    trainer = Trainer(cfg)
    training_data = load_data(
        "/Users/melinda/rasa/data/test/lookup_tables/lookup_table.md"
    )
    with pytest.warns(UserWarning) as record:
        validate_required_components_from_data(trainer.pipeline, training_data)

    assert len(record) == 1


def test_warn_missing_synonym_mapper():
    cfg = config.load("sample_configs/config_crf_no_synonyms.yml")
    trainer = Trainer(cfg)
    training_data = load_data("data/test/markdown_single_sections/synonyms_only.md")
    with pytest.warns(UserWarning) as record:
        validate_required_components_from_data(trainer.pipeline, training_data)

    assert len(record) == 1


def test_warn_missing_response_selector():
    cfg = config.load("sample_configs/config_supervised_embeddings.yml")
    trainer = Trainer(cfg)
    training_data = load_data("data/examples/rasa")
    with pytest.warns(UserWarning) as record:
        validate_required_components_from_data(trainer.pipeline, training_data)

    assert len(record) == 1

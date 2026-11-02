#!/usr/bin/env python3
"""Validate workflow YAML without invoking skills or evaluating runtime results."""
import argparse
import json
from pathlib import Path
import re
import sys

IDENTIFIER = re.compile(r'[a-z][a-z0-9_-]*\Z')
SKILL_NAME = re.compile(r'[a-z0-9][a-z0-9-]*(?::[a-z0-9][a-z0-9-]*)?\Z')
FIELDS = {'status', 'changed', 'has_findings', 'has_unresolved'}
STATUSES = {'completed', 'skipped', 'blocked', 'failed'}


class InvalidWorkflow(ValueError):
    pass


def require(test, message):
    if not test:
        raise InvalidWorkflow(message)


def text_value(value, where):
    require(isinstance(value, str) and bool(value.strip()), f'{where}: expected non-empty text')


def mapping(value, allowed, required, where):
    require(isinstance(value, dict), f'{where}: expected mapping')
    require(all(isinstance(k, str) for k in value), f'{where}: keys must be strings')
    require(not (set(value) - allowed), f'{where}: unknown fields {sorted(set(value) - allowed)}')
    require(not (required - set(value)), f'{where}: missing fields {sorted(required - set(value))}')


def nonempty_list(value, where):
    require(isinstance(value, list) and bool(value), f'{where}: expected non-empty list')


def condition(value, previous, where, depth=0):
    require(depth < 8, f'{where}: maximum condition nesting is 8')
    require(isinstance(value, dict), f'{where}: expected condition mapping')
    if set(value) in ({'all'}, {'any'}):
        operator = next(iter(value))
        nonempty_list(value[operator], f'{where}.{operator}')
        for index, child in enumerate(value[operator]):
            condition(child, previous, f'{where}.{operator}[{index}]', depth + 1)
        return
    mapping(value, {'step', 'field', 'equals'}, {'step', 'field', 'equals'}, where)
    text_value(value['step'], f'{where}.step')
    require(value['step'] in previous, f'{where}.step: must reference an earlier step')
    field = value['field']
    require(isinstance(field, str) and field in FIELDS, f'{where}.field: unsupported result field')
    expected = value['equals']
    if field == 'status':
        require(isinstance(expected, str) and expected in STATUSES, f'{where}.equals: unsupported status')
    else:
        require(type(expected) is bool, f'{where}.equals: expected literal true or false')


def validate(data):
    mapping(data, {'version', 'name', 'description', 'steps'}, {'version', 'name', 'steps'}, 'workflow')
    require(type(data['version']) is int and data['version'] == 1, 'version: only integer 1 is supported')
    text_value(data['name'], 'name')
    require(bool(IDENTIFIER.fullmatch(data['name'])), 'name: use lowercase identifier')
    if 'description' in data:
        text_value(data['description'], 'description')
    nonempty_list(data['steps'], 'steps')
    previous, skill_names = [], []
    for index, step in enumerate(data['steps']):
        where = f'steps[{index}]'
        mapping(step, {'id', 'name', 'when', 'skills'}, {'id', 'skills'}, where)
        text_value(step['id'], f'{where}.id')
        require(bool(IDENTIFIER.fullmatch(step['id'])), f'{where}.id: use lowercase identifier')
        require(step['id'] not in previous, f'{where}.id: duplicate step id')
        if 'name' in step:
            text_value(step['name'], f'{where}.name')
        if 'when' in step:
            condition(step['when'], previous, f'{where}.when')
        nonempty_list(step['skills'], f'{where}.skills')
        for skill_index, skill in enumerate(step['skills']):
            location = f'{where}.skills[{skill_index}]'
            mapping(skill, {'name', 'instruction'}, {'name', 'instruction'}, location)
            text_value(skill['name'], f'{location}.name')
            require(bool(SKILL_NAME.fullmatch(skill['name'])), f'{location}.name: expected skill identifier, not path')
            text_value(skill['instruction'], f'{location}.instruction')
            if skill['name'] not in skill_names:
                skill_names.append(skill['name'])
        previous.append(step['id'])
    return previous, skill_names


def load_yaml(source):
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError('PyYAML 6 is required; use an existing project/isolated Python environment, or manually validate the documented format') from exc

    class WorkflowLoader(yaml.SafeLoader):
        # Restrict boolean spelling without changing PyYAML's process-global loader.
        yaml_implicit_resolvers = {
            key: [(tag, pattern) for tag, pattern in rules if tag != 'tag:yaml.org,2002:bool']
            for key, rules in yaml.SafeLoader.yaml_implicit_resolvers.items()
        }

    WorkflowLoader.add_implicit_resolver('tag:yaml.org,2002:bool', re.compile(r'^(?:true|false)$'), ['t', 'f'])

    def unique_mapping(loader, node):
        result = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=True)
            require(isinstance(key, str), 'YAML mapping keys must be strings')
            require(key not in result, f'YAML duplicate key: {key}')
            result[key] = loader.construct_object(value_node, deep=True)
        return result

    WorkflowLoader.add_constructor('tag:yaml.org,2002:map', unique_mapping)
    try:
        for event in yaml.parse(source):
            require(not isinstance(event, yaml.AliasEvent) and not getattr(event, 'anchor', None),
                    'YAML anchors and aliases are unsupported')
            require(not getattr(event, 'tag', None), 'Explicit YAML tags are unsupported')
        return yaml.load(source, Loader=WorkflowLoader)
    except yaml.YAMLError as exc:
        raise InvalidWorkflow(f'YAML: {exc}') from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workflow', type=Path)
    parser.add_argument('--json', action='store_true', help='Print one JSON result')
    args = parser.parse_args()
    result = {'valid': False, 'steps': [], 'skills': [], 'errors': []}
    code = 0
    try:
        with args.workflow.open('rb') as stream:
            raw = stream.read(1024 * 1024 + 1)
        require(len(raw) <= 1024 * 1024, 'workflow: maximum size is 1 MiB')
        data = load_yaml(raw.decode('utf-8-sig'))
        result['steps'], result['skills'] = validate(data)
        result['valid'] = True
    except (ValueError, RecursionError) as exc:
        result['errors'].append(str(exc))
        code = 1
    except (OSError, RuntimeError) as exc:
        result['errors'].append(str(exc))
        code = 2
    if args.json:
        print(json.dumps(result, ensure_ascii=True))
    elif result['valid']:
        print(f"Valid workflow: {len(result['steps'])} steps; structure only, skills and runtime evidence not checked.")
    else:
        print('\n'.join(result['errors']))
    return code


if __name__ == '__main__':
    sys.exit(main())

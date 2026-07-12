from demiplane.functions.functions import uuid
from demiplane.functions.validators import clamp_int, parse_optional_int, is_valid_uuid


class AbilitiesMixin:
    def save_ability_values(self, character_id: str, request_form):
        import math
        character = self.store.go_get_one('character', {'id': character_id})
        character_proficiency = 0
        if character:
            character_proficiency = parse_optional_int(character.get('proficiency'), fallback=0)
            if character_proficiency is None:
                character_proficiency = 0

        for ability in self.ABILITY_TO_SKILL_MAPPING:
            existing_ability = self.store.go_get_one(ability, {"character_id": character_id})
            existing_skills = self.store.go_get_one(f"{ability}_skills", {f"{ability}_id": existing_ability['id']}) if existing_ability else None

            raw_value = request_form.get(f'{ability}-value')
            has_ability_value = f'{ability}-value' in request_form
            has_saving_throw_toggle = f'{ability}-proficient' in request_form
            has_any_skill_toggle = any(
                f"{ability}_skills-{skill}_proficient" in request_form
                for skill in self.ABILITY_TO_SKILL_MAPPING[ability]
            )

            # Ignore untouched abilities so partial row updates do not zero out
            # proficiency flags on other abilities.
            if not (has_ability_value or has_saving_throw_toggle or has_any_skill_toggle):
                continue

            existing_value_fallback = 10
            if existing_ability:
                existing_value_fallback = clamp_int(existing_ability.get('value'), 1, 30, fallback=10)

            if raw_value is None or str(raw_value).strip() == '':
                if not existing_ability:
                    continue
                value = existing_value_fallback
            else:
                # Preserve the current ability score when the posted value is malformed.
                value = clamp_int(raw_value, 1, 30, fallback=existing_value_fallback)

            # Ability scores are 1-30 in D&D 5e; clamp to that range

            modifier = math.floor((value - 10) / 2)

            if has_ability_value or has_saving_throw_toggle:
                saving_proficient = 1 if request_form.get(f"{ability}-proficient") == "1" else 0
            elif existing_ability:
                saving_proficient = 1 if existing_ability.get('proficient') else 0
            else:
                saving_proficient = 0

            character_ability = {
                "id": "",
                "character_id": character_id,
                "value": value,
                "modifier": modifier,
                "proficient": int(saving_proficient),
            }

            if existing_ability:
                ability_id = existing_ability['id']
                character_ability['id'] = ability_id
                self.store.go_update(ability, character_ability)
            else:
                ability_id = uuid()
                character_ability['id'] = ability_id
                self.store.go_add_new(ability, character_ability)

            skills = self.store.go_get_one(f"{ability}_skills", {f"{ability}_id": ability_id})

            modifier_score = modifier
            saving_proficient_score = 0
            if saving_proficient:
                saving_proficient_score += character_proficiency

            characters_skills = {
                "id": "",
                f"{ability}_id": ability_id,
                "saving_throw": modifier_score + saving_proficient_score,
            }

            for skill in self.ABILITY_TO_SKILL_MAPPING[ability]:
                skill_toggle_key = f'{ability}_skills-{skill}_proficient'
                if has_ability_value or skill_toggle_key in request_form:
                    skill_proficient = 1 if request_form.get(skill_toggle_key) == "1" else 0
                elif existing_skills:
                    skill_proficient = 1 if existing_skills.get(f'{skill}_proficient') else 0
                else:
                    skill_proficient = 0

                skill_proficient_score = character_proficiency if skill_proficient else 0

                characters_skills[skill] = modifier_score + skill_proficient_score
                characters_skills[f"{skill}_proficient"] = int(skill_proficient)

            if skills:
                skill_id = skills['id']
                characters_skills['id'] = skill_id
                self.store.go_update(f"{ability}_skills", characters_skills)
            else:
                skill_id = uuid()
                characters_skills['id'] = skill_id
                self.store.go_add_new(f"{ability}_skills", characters_skills)

    def _recalculate_ability_skill_scores(self, character_id: str):
        import math

        if not is_valid_uuid(character_id):
            return

        character = self.store.go_get_one('character', {'id': character_id})
        if not character:
            return

        character_proficiency = parse_optional_int(character.get('proficiency'), fallback=0)
        if character_proficiency is None:
            character_proficiency = 0

        for ability_name, skill_list in self.ABILITY_TO_SKILL_MAPPING.items():
            ability_row = self.store.go_get_one(ability_name, {'character_id': character_id})
            if not ability_row:
                continue

            ability_id = ability_row.get('id')
            if not is_valid_uuid(ability_id):
                continue

            ability_value = clamp_int(ability_row.get('value'), 1, 30, fallback=10)
            modifier = math.floor((ability_value - 10) / 2)
            saving_proficient = 1 if ability_row.get('proficient') else 0

            # Keep stored ability modifier in sync with ability value.
            self.store.go_update(ability_name, {
                'id': ability_id,
                'modifier': modifier,
            })

            skills_table = f'{ability_name}_skills'
            existing_skills = self.store.go_get_one(skills_table, {f'{ability_name}_id': ability_id}) or {}
            existing_skills_id = existing_skills.get('id')

            recalculated_skills = {
                'id': existing_skills_id if is_valid_uuid(existing_skills_id) else uuid(),
                f'{ability_name}_id': ability_id,
                'saving_throw': modifier + (character_proficiency if saving_proficient else 0),
            }

            for skill in skill_list:
                skill_proficient = 1 if existing_skills.get(f'{skill}_proficient') else 0
                recalculated_skills[skill] = modifier + (character_proficiency if skill_proficient else 0)
                recalculated_skills[f'{skill}_proficient'] = skill_proficient

            if is_valid_uuid(existing_skills_id):
                self.store.go_update(skills_table, recalculated_skills)
            else:
                self.store.go_add_new(skills_table, recalculated_skills)

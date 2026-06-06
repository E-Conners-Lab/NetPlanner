"""Phase 3 — garak generator that red-teams the *real* Advisor guardrails.

Stock garak NIM generators send each probe as a bare user turn, so the probes
hit an undefended model. NetPlanner's Advisor ships a hardened system prompt
(PIS-17 role anchor + PIS-24 hard-stop guardrails + the untrusted-data fence),
and the engagement's question is whether *those* guardrails survive attack
(AI-1). This generator subclasses the NIM chat generator and prepends the
Advisor system prompt to every conversation, so prompt-injection / jailbreak
probes attack the production posture, not a bare endpoint.

The system prompt is read from the file named by ``ADVISOR_SYSTEM_PROMPT_FILE``
(produced by ``backend/scripts/export_advisor_prompt.py``) so it can never drift
from the application code.

Install (the run script does this): copy this file into garak's generator
namespace, then select it with ``--model_type advisor_nim.AdvisorNIM``.

    cp advisor_nim.py "$(python -c 'import garak,os;print(os.path.dirname(garak.__file__))')/generators/"
"""

from __future__ import annotations

import logging
import os
from typing import List, Union

from garak import _config
from garak.attempt import Conversation, Message, Turn
from garak.generators.nim import NVOpenAIChat

logger = logging.getLogger(__name__)

_ENV_PROMPT_FILE = "ADVISOR_SYSTEM_PROMPT_FILE"


class AdvisorNIM(NVOpenAIChat):
    """NIM chat generator that injects NetPlanner's Advisor system prompt.

    Every probe conversation gains a leading ``system`` turn carrying the real
    Advisor guardrails (unless the probe already set one — e.g. the
    ``sysprompt_extraction`` probes supply their own), so the red-team measures
    the defended posture.
    """

    generator_family_name = "AdvisorNIM"

    def __init__(self, name: str = "", config_root=_config) -> None:
        super().__init__(name, config_root=config_root)
        self._advisor_system_prompt = self._load_system_prompt()

    @staticmethod
    def _load_system_prompt() -> str:
        path = os.environ.get(_ENV_PROMPT_FILE, "")
        if not path or not os.path.isfile(path):
            raise FileNotFoundError(
                f"{_ENV_PROMPT_FILE} must point to the exported Advisor system "
                "prompt (run backend/scripts/export_advisor_prompt.py). "
                f"Got: {path!r}"
            )
        with open(path, encoding="utf-8") as handle:
            prompt = handle.read().strip()
        logger.info("AdvisorNIM loaded system prompt (%d chars)", len(prompt))
        return prompt

    def _call_model(
        self,
        prompt: Union[Conversation, List[dict]],
        generations_this_call: int = 1,
    ) -> List[Union[Message, None]]:
        if isinstance(prompt, Conversation) and not any(
            turn.role == "system" for turn in prompt.turns
        ):
            prompt = Conversation(
                turns=[
                    Turn(
                        role="system", content=Message(text=self._advisor_system_prompt)
                    ),
                    *prompt.turns,
                ],
                notes=prompt.notes,
            )
        return super()._call_model(prompt, generations_this_call)

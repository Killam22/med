# diagnostic_ai/services/genetic/chromosome.py

import random
from dataclasses import dataclass, field


@dataclass
class Chromosome:
    temperature:   float
    top_p:         float
    retrieval_k:   int
    prompt_style:  int
    history_len:   int
    fitness_score: float = field(default=0.0)

    @classmethod
    def random(cls) -> "Chromosome":
        return cls(
            temperature  = round(random.uniform(0.1, 1.0), 2),
            top_p        = round(random.uniform(0.7, 1.0), 2),
            retrieval_k  = random.randint(3, 10),
            prompt_style = random.randint(1, 2),
            history_len  = random.choice([2, 4, 6, 8]),
        )

    def to_dict(self) -> dict:
        return {
            "temperature":   self.temperature,
            "top_p":         self.top_p,
            "retrieval_k":   self.retrieval_k,
            "prompt_style":  self.prompt_style,
            "history_len":   self.history_len,
            "fitness_score": self.fitness_score,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Chromosome":
        return cls(
            temperature   = d["temperature"],
            top_p         = d["top_p"],
            retrieval_k   = d["retrieval_k"],
            prompt_style  = d["prompt_style"],
            history_len   = d["history_len"],
            fitness_score = d.get("fitness_score", 0.0),
        )

    def __repr__(self):
        return (
            f"Chromosome(temp={self.temperature}, top_p={self.top_p}, "
            f"k={self.retrieval_k}, style={self.prompt_style}, "
            f"hist={self.history_len}, fitness={self.fitness_score:.4f})"
        )

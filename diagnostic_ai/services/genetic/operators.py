# diagnostic_ai/services/genetic/operators.py

import random
import logging
from .chromosome import Chromosome

logger = logging.getLogger(__name__)


def selection_tournament(population: list, k: int = 3) -> Chromosome:
    candidates = random.sample(population, min(k, len(population)))
    winner     = max(candidates, key=lambda c: c.fitness_score)
    logger.debug("Tournament → gagnant: fitness=%.4f", winner.fitness_score)
    return winner


def crossover_uniform(parent1: Chromosome, parent2: Chromosome) -> Chromosome:
    child = Chromosome(
        temperature  = parent1.temperature  if random.random() > 0.5 else parent2.temperature,
        top_p        = parent1.top_p        if random.random() > 0.5 else parent2.top_p,
        retrieval_k  = parent1.retrieval_k  if random.random() > 0.5 else parent2.retrieval_k,
        prompt_style = parent1.prompt_style if random.random() > 0.5 else parent2.prompt_style,
        history_len  = parent1.history_len  if random.random() > 0.5 else parent2.history_len,
    )
    logger.debug("Crossover → enfant: %s", child)
    return child


def mutate(chromosome: Chromosome, rate: float = 0.15) -> Chromosome:
    c = Chromosome.from_dict(chromosome.to_dict())

    if random.random() < rate:
        c.temperature = round(max(0.1, min(1.0, c.temperature + random.gauss(0, 0.1))), 2)

    if random.random() < rate:
        c.top_p = round(max(0.7, min(1.0, c.top_p + random.gauss(0, 0.05))), 2)

    if random.random() < rate:
        c.retrieval_k = max(3, min(10, c.retrieval_k + random.choice([-1, 0, 1])))

    if random.random() < rate:
        c.prompt_style = random.randint(1, 2)

    if random.random() < rate:
        c.history_len = random.choice([2, 4, 6, 8])

    if c.to_dict() != chromosome.to_dict():
        logger.debug("Mutation appliquée: %s → %s", chromosome, c)

    return c


def elitism(population: list, n: int = 2) -> list:
    elite = sorted(population, key=lambda c: c.fitness_score, reverse=True)[:n]
    logger.debug("Élites: %s", [f"fitness={e.fitness_score:.4f}" for e in elite])
    return elite

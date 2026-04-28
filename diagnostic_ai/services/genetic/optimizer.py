# diagnostic_ai/services/genetic/optimizer.py

import logging
from .chromosome import Chromosome
from .fitness import evaluate
from .operators import selection_tournament, crossover_uniform, mutate, elitism

logger = logging.getLogger(__name__)

DEFAULT_AG_PARAMS = {
    "population_size": 5,
    "generations":     3,
    "mutation_rate":   0.15,
    "elite_count":     2,
}

MAX_TEST_CASES_PER_EVAL = 2

BASE_TEST_CASES = [
    {
        "symptoms":          "fever headache cough fatigue body aches",
        "lang":              "fr",
        "expected_diseases": ["Influenza", "Common Cold", "Malaria"],
    },
    {
        "symptoms":          "chest pain shortness of breath dizziness sweating",
        "lang":              "fr",
        "expected_diseases": ["Heart Attack", "Angina", "Hypertension"],
    },
    {
        "symptoms":          "abdominal pain nausea vomiting fever right side",
        "lang":              "fr",
        "expected_diseases": ["Appendicitis", "Gastroenteritis"],
    },
    {
        "symptoms":          "skin rash itching redness swelling",
        "lang":              "ar",
        "expected_diseases": ["Allergy", "Psoriasis", "Eczema"],
    },
    {
        "symptoms":          "frequent urination excessive thirst fatigue weight loss",
        "lang":              "fr",
        "expected_diseases": ["Diabetes", "Type 2 Diabetes"],
    },
]


def get_test_cases() -> list:
    test_cases = BASE_TEST_CASES.copy()
    try:
        from diagnostic_ai.models import TrainingData
        training = TrainingData.objects.order_by("-quality_score")[:5]
        for t in training:
            test_cases.append({
                "symptoms":          t.symptoms,
                "lang":              t.lang,
                "expected_diseases": [d.get("name_en", "") for d in t.diseases[:3]],
            })
    except Exception as e:
        logger.warning("Impossible de charger TrainingData: %s", e)

    return test_cases[:MAX_TEST_CASES_PER_EVAL]


class GeneticOptimizer:

    def __init__(self, params: dict = None):
        p = {**DEFAULT_AG_PARAMS, **(params or {})}
        self.population_size = p["population_size"]
        self.generations     = p["generations"]
        self.mutation_rate   = p["mutation_rate"]
        self.elite_count     = p["elite_count"]
        self.test_cases      = get_test_cases()
        self.history         = []

    def _init_population(self) -> list:
        population = [Chromosome.random() for _ in range(self.population_size)]
        logger.info("Population initialisée: %d individus", len(population))
        return population

    def _evaluate_all(self, population: list) -> list:
        for i, chromosome in enumerate(population):
            logger.info("Évaluation [%d/%d]: %s", i + 1, len(population), chromosome)
            chromosome.fitness_score = evaluate(chromosome, self.test_cases)
            logger.info("  → fitness = %.4f", chromosome.fitness_score)
        return population

    def _create_next_generation(self, population: list) -> list:
        new_population = elitism(population, self.elite_count)
        while len(new_population) < self.population_size:
            parent1 = selection_tournament(population)
            parent2 = selection_tournament(population)
            child   = crossover_uniform(parent1, parent2)
            child   = mutate(child, self.mutation_rate)
            new_population.append(child)
        return new_population

    def run(self) -> dict:
        logger.info(
            "═══ Démarrage AG ═══ population=%d, générations=%d, mutation=%.0f%%",
            self.population_size, self.generations, self.mutation_rate * 100
        )

        population = self._init_population()

        for gen in range(1, self.generations + 1):
            logger.info("═══ Génération %d/%d ═══", gen, self.generations)
            population = self._evaluate_all(population)

            best = max(population, key=lambda c: c.fitness_score)
            avg  = sum(c.fitness_score for c in population) / len(population)

            self.history.append({
                "generation":   gen,
                "best_fitness": best.fitness_score,
                "avg_fitness":  round(avg, 4),
                "best_params":  best.to_dict(),
            })

            logger.info("Génération %d — meilleur: %.4f | moyenne: %.4f", gen, best.fitness_score, avg)

            if best.fitness_score >= 0.95:
                logger.info("Convergence atteinte à la génération %d", gen)
                break

            if gen < self.generations:
                population = self._create_next_generation(population)

        best_chromosome = max(population, key=lambda c: c.fitness_score)
        logger.info("═══ Optimisation terminée ═══\n Meilleur: %s", best_chromosome)

        return {
            "best_chromosome": best_chromosome.to_dict(),
            "history":         self.history,
            "generations_run": len(self.history),
        }


def get_best_params() -> dict:
    try:
        from diagnostic_ai.models import GeneticRun
        latest = GeneticRun.objects.order_by("-best_fitness").first()
        if latest:
            logger.debug("Paramètres AG chargés: fitness=%.4f", latest.best_fitness)
            return latest.best_chromosome
    except Exception as e:
        logger.warning("Impossible de charger GeneticRun: %s", e)

    return {
        "temperature":   0.7,
        "top_p":         0.9,
        "retrieval_k":   5,
        "prompt_style":  2,
        "history_len":   4,
        "fitness_score": 0.0,
    }

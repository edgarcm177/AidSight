from typing import Dict, Any
import numpy as np
import pandas as pd


def load_embedding_model():
    """
    Placeholder for sentence-transformers or similar.
    """
    return None


def embed_projects(df: pd.DataFrame, model) -> np.ndarray:
    """
    Return a matrix of embeddings for project descriptions.
    """
    # TODO: real embeddings
    return np.zeros((len(df), 16))


def find_success_twin(
    projects_df: pd.DataFrame,
    target_project_id: str,
) -> Dict[str, Any]:
    """
    Find a 'Success Twin' project for the given project_id.
    Placeholder: just return a random other project.
    """
    if target_project_id not in projects_df["id"].values:
        raise ValueError("target_project_id not found")

    # Here you would use embeddings & similarity search
    candidate = projects_df[projects_df["id"] != target_project_id].iloc[0]

    return {
        "target_project_id": target_project_id,
        "twin_project_id": candidate["id"],
        "similarity_score": 0.7,
        "bullets": [
            "Survived past inflation shock.",
            "Used decentralized delivery model.",
        ],
    }

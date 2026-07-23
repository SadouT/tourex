#!/usr/bin/env python3
"""Script de test de l'API Groq.

Prerequis :
    pip install groq

Utilisation :
    export GROQ_API_KEY="votre_nouvelle_cle"   # NE JAMAIS ecrire la cle en dur
    python test_groq_api.py
    python test_groq_api.py "Explique-moi la gravite en une phrase"

La cle est lue uniquement depuis la variable d'environnement GROQ_API_KEY.
Ne committez jamais une cle API dans le code source.
"""

import os
import sys

try:
    from groq import Groq
except ImportError:
    sys.exit("Le paquet 'groq' n'est pas installe. Lancez : pip install groq")


# Modele Groq par defaut (rapide et gratuit sur le tier de dev)
DEFAULT_MODEL = "llama-3.3-70b-versatile"


def main() -> int:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Erreur : la variable d'environnement GROQ_API_KEY n'est pas definie.")
        print('Definissez-la avec :  export GROQ_API_KEY="votre_cle"')
        return 1

    # Le prompt peut etre passe en argument, sinon on utilise un message de test.
    prompt = " ".join(sys.argv[1:]) or "Dis bonjour et confirme que l'API fonctionne."

    client = Groq(api_key=api_key)

    print(f"Modele    : {DEFAULT_MODEL}")
    print(f"Prompt    : {prompt}")
    print("-" * 50)

    try:
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": "Tu es un assistant concis et utile."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=512,
        )
    except Exception as exc:  # erreurs reseau / authentification / quota
        print(f"Echec de l'appel API : {exc}")
        return 1

    message = response.choices[0].message.content
    usage = response.usage

    print("Reponse :")
    print(message)
    print("-" * 50)
    if usage is not None:
        print(
            f"Tokens -> prompt: {usage.prompt_tokens}, "
            f"reponse: {usage.completion_tokens}, "
            f"total: {usage.total_tokens}"
        )
    print("Test termine avec succes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

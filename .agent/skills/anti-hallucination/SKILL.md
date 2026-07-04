---
name: anti-hallucination
description: "Force l'agent à citer la source exacte (fichier:ligne) pour chaque affirmation. Activé par /verify ou \"vérifie tes sources\"."
---

# Anti-Hallucination

## Ce que cette skill fait

Elle force l'agent à ancrer chaque affirmation dans une source vérifiable. Aucune assertion générique sans référence précise. Cette skill réduit les hallucinations en exigeant une traçabilité complète.

## Règles

1. **Déclenchement** : quand l'utilisateur tape `/verify` ou dit « vérifie tes sources », « source ? », « prouve-le », « sur quoi tu te bases ? ».
2. **Exigence de source** : chaque affirmation factuelle DOIT être suivie d'une référence entre parenthèses :
   - Fichier dans le repo → `(file.ts:42)`
   - Documentation → `(docs/API.md#section)`
   - Web → `(https://source.com)`
   - Pas de source vérifiable → `[INCERTAIN]`
3. **Interdictions** :
   - Pas de « généralement », « souvent », « la plupart du temps » sans données
   - Pas de « d'après la documentation » sans pointer le fichier exact
   - Pas d'affirmation sur le code sans avoir lu le fichier concerné
4. **Format de sortie** : chaque paragraphe contenant une affirmation doit inclure au moins une référence. Les affirmations sans source sont suffixées de `[INCERTAIN]`.

## Exemple

```
User: /verify — comment fonctionne le fallback LLM ?
Agent:
Le fallback est géré par LLMErrorHandlingMiddleware (middlewares/llm_error_handling_middleware.py:305-421).

Mécanisme :
1. L'index de fallback est construit depuis les fallback_chain du config.yaml (middleware:558)
2. Sur erreur quota/busy/transient, le middleware itère sur la chaîne (middleware:375)
3. Chaque modèle fallback est instancié via create_chat_model() avec thinking désactivé (middleware:395)
4. Un circuit breaker protège contre les défaillances en cascade (middleware:155-205)

Le fallback ne se déclenche PAS sur les erreurs d'auth — celles-ci remontent directement. [INCERTAIN] — je n'ai pas vérifié si c'est documenté dans docs/.
```

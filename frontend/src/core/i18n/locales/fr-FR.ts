import {
  CompassIcon,
  GraduationCapIcon,
  ImageIcon,
  MicroscopeIcon,
  PenLineIcon,
  ShapesIcon,
  SparklesIcon,
  VideoIcon,
} from "lucide-react";

import type { Translations } from "./types";

export const frFR: Translations = {
  // Locale meta
  locale: {
    localName: "Français",
  },

  // Common
  common: {
    home: "Accueil",
    settings: "Paramètres",
    delete: "Supprimer",
    edit: "Modifier",
    rename: "Renommer",
    share: "Partager",
    openInNewWindow: "Ouvrir dans une nouvelle fenêtre",
    close: "Fermer",
    more: "Plus",
    search: "Rechercher",
    loadMore: "Charger plus",
    download: "Télécharger",
    thinking: "Réflexion",
    artifacts: "Artefacts",
    public: "Public",
    custom: "Personnalisé",
    notAvailableInDemoMode: "Non disponible en mode démonstration",
    loading: "Chargement…",
    version: "Version",
    lastUpdated: "Dernière mise à jour",
    code: "Code",
    preview: "Aperçu",
    cancel: "Annuler",
    save: "Enregistrer",
    install: "Installer",
    create: "Créer",
    import: "Importer",
    export: "Exporter",
    exportAsMarkdown: "Exporter en Markdown",
    exportAsJSON: "Exporter en JSON",
    exportSuccess: "Conversation exportée",
  },

  // Home
  home: {
    docs: "Documentation",
    blog: "Blog",
  },

  // Welcome
  welcome: {
    greeting: "Bonjour, ravi de vous revoir !",
    description:
      "Bienvenue sur 🦌 DeerFlow, un super agent open source. Grâce à des skills intégrées et personnalisables,\nDeerFlow vous aide à rechercher sur le web, analyser des données et générer des artefacts\ncomme des présentations, des pages web, et bien plus encore.",

    createYourOwnSkill: "Créez votre propre Skill",
    createYourOwnSkillDescription:
      "Créez votre propre skill pour libérer tout le potentiel de DeerFlow. Avec des skills personnalisées,\nDeerFlow peut vous aider à rechercher sur le web, analyser des données et générer\n des artefacts comme des présentations, des pages web, et bien plus encore.",
  },

  // Clipboard
  clipboard: {
    copyToClipboard: "Copier dans le presse-papiers",
    copiedToClipboard: "Copié dans le presse-papiers",
    failedToCopyToClipboard: "Échec de la copie dans le presse-papiers",
    linkCopied: "Lien copié dans le presse-papiers",
  },

  // Input Box
  inputBox: {
    placeholder: "Comment puis-je vous aider aujourd'hui ?",
    createSkillPrompt:
      "Nous allons créer une nouvelle skill étape par étape avec `skill-creator`. Pour commencer, que souhaitez-vous que cette skill fasse ?",
    addAttachments: "Ajouter des pièces jointes",
    mode: "Mode",
    flashMode: "Flash",
    flashModeDescription: "Rapide et efficace, mais peut manquer de précision",
    reasoningMode: "Raisonnement",
    reasoningModeDescription:
      "Réflexion avant d'agir, équilibre entre rapidité et précision",
    proMode: "Pro",
    proModeDescription:
      "Raisonnement, planification et exécution pour des résultats plus précis, peut prendre plus de temps",
    ultraMode: "Ultra",
    ultraModeDescription:
      "Mode Pro avec sous-agents pour répartir le travail ; idéal pour les tâches complexes en plusieurs étapes",
    reasoningEffort: "Effort de raisonnement",
    reasoningEffortMinimal: "Minimal",
    reasoningEffortMinimalDescription: "Récupération + Sortie directe",
    reasoningEffortLow: "Faible",
    reasoningEffortLowDescription: "Vérification logique simple + Déduction superficielle",
    reasoningEffortMedium: "Moyen",
    reasoningEffortMediumDescription:
      "Analyse logique multi-niveaux + Vérification de base",
    reasoningEffortHigh: "Élevé",
    reasoningEffortHighDescription:
      "Déduction logique multi-dimensionnelle + Vérification multi-chemins + Contrôle inverse",
    searchModels: "Rechercher des modèles…",
    surpriseMe: "Surprise",
    surpriseMePrompt: "Surprenez-moi",
    followupLoading: "Génération des questions de suivi…",
    followupConfirmTitle: "Envoyer la suggestion ?",
    followupConfirmDescription:
      "Vous avez déjà du texte dans le champ de saisie. Choisissez comment l'envoyer.",
    followupConfirmAppend: "Ajouter et envoyer",
    followupConfirmReplace: "Remplacer et envoyer",
    suggestions: [
      {
        suggestion: "Rédiger",
        prompt: "Rédige un article de blog sur les dernières tendances concernant [sujet]",
        icon: PenLineIcon,
      },
      {
        suggestion: "Rechercher",
        prompt:
          "Effectue une recherche approfondie sur [sujet] et résume les conclusions.",
        icon: MicroscopeIcon,
      },
      {
        suggestion: "Collecter",
        prompt: "Collecte des données depuis [source] et crée un rapport.",
        icon: ShapesIcon,
      },
      {
        suggestion: "Apprendre",
        prompt: "Apprends-moi [sujet] et crée un tutoriel.",
        icon: GraduationCapIcon,
      },
    ],
    suggestionsCreate: [
      {
        suggestion: "Page web",
        prompt: "Crée une page web sur [sujet]",
        icon: CompassIcon,
      },
      {
        suggestion: "Image",
        prompt: "Crée une image sur [sujet]",
        icon: ImageIcon,
      },
      {
        suggestion: "Vidéo",
        prompt: "Crée une vidéo sur [sujet]",
        icon: VideoIcon,
      },
      {
        type: "separator",
      },
      {
        suggestion: "Skill",
        prompt:
          "Nous allons créer une nouvelle skill étape par étape avec `skill-creator`. Pour commencer, que souhaitez-vous que cette skill fasse ?",
        icon: SparklesIcon,
      },
    ],
  },

  // Sidebar
  sidebar: {
    newChat: "Nouvelle conversation",
    chats: "Conversations",
    channels: "Canaux",
    recentChats: "Conversations récentes",
    demoChats: "Conversations de démonstration",
    agents: "Agents",
  },

  // Agents
  agents: {
    title: "Agents",
    description:
      "Créez et gérez des agents personnalisés avec des prompts et des capacités spécialisés.",
    newAgent: "Nouvel agent",
    emptyTitle: "Aucun agent personnalisé pour l'instant",
    emptyDescription:
      "Créez votre premier agent personnalisé avec un prompt système spécialisé.",
    chat: "Conversation",
    delete: "Supprimer",
    deleteConfirm:
      "Êtes-vous sûr de vouloir supprimer cet agent ? Cette action est irréversible.",
    deleteSuccess: "Agent supprimé",
    newChat: "Nouvelle conversation",
    createPageTitle: "Concevez votre agent",
    createPageSubtitle:
      "Décrivez l'agent que vous souhaitez — je vous aiderai à le créer par la conversation.",
    nameStepTitle: "Donnez un nom à votre nouvel agent",
    nameStepHint:
      "Lettres, chiffres et tirets uniquement — stocké en minuscules (ex. : code-reviewer)",
    nameStepPlaceholder: "ex. : code-reviewer",
    nameStepContinue: "Continuer",
    nameStepInvalidError:
      "Nom invalide — utilisez uniquement des lettres, des chiffres et des tirets",
    nameStepAlreadyExistsError: "Un agent avec ce nom existe déjà",
    nameStepNetworkError:
      "La requête réseau a échoué — vérifiez votre réseau ou la connexion au backend",
    nameStepCheckError: "Impossible de vérifier la disponibilité du nom — veuillez réessayer",
    nameStepCheckErrorWithDetail: "Vérification du nom échouée : {detail}",
    nameStepApiDisabledError:
      "La gestion des agents personnalisés n'est pas activée sur ce serveur. Contactez votre administrateur.",
    nameStepBootstrapMessage:
      "Le nom du nouvel agent personnalisé est {name}. Aidez-moi à concevoir son rôle, son comportement et son SOUL.md avant de l'enregistrer.",
    save: "Enregistrer l'agent",
    saving: "Enregistrement de l'agent…",
    saveRequested:
      "Enregistrement demandé. DeerFlow génère et sauvegarde une première version maintenant.",
    saveHint:
      "Vous pouvez enregistrer cet agent à tout moment depuis le menu en haut à droite, même s'il ne s'agit que d'une première ébauche.",
    saveCommandMessage:
      "Veuillez enregistrer cet agent personnalisé maintenant en vous basant sur tout ce que nous avons discuté jusqu'à présent. Considérez ceci comme ma confirmation explicite de sauvegarde. Si certains détails manquent encore, faites des hypothèses raisonnables, générez un premier SOUL.md concis en anglais et appelez immédiatement setup_agent sans me demander de confirmation supplémentaire.",
    agentCreatedPendingRefresh:
      "L'agent a été créé, mais DeerFlow n'a pas encore pu le charger. Veuillez actualiser cette page dans un moment.",
    more: "Plus d'actions",
    agentCreated: "Agent créé !",
    startChatting: "Commencer la conversation",
    backToGallery: "Retour à la galerie",
  },

  // Breadcrumb
  breadcrumb: {
    workspace: "Espace de travail",
    chats: "Conversations",
  },

  // Workspace
  workspace: {
    officialWebsite: "Site officiel de DeerFlow",
    githubTooltip: "DeerFlow sur Github",
    settingsAndMore: "Paramètres et plus",
    visitGithub: "DeerFlow sur GitHub",
    reportIssue: "Signaler un problème",
    contactUs: "Nous contacter",
    about: "À propos de DeerFlow",
    logout: "Se déconnecter",
    gatewayUnavailable: "La passerelle est temporairement indisponible.",
    gatewayUnavailableRetrying: "Nouvelle tentative en arrière-plan…",
  },

  // Conversation
  conversation: {
    noMessages: "Aucun message pour l'instant",
    startConversation: "Démarrez une conversation pour voir les messages ici",
  },

  // Chats
  chats: {
    searchChats: "Rechercher des conversations",
    loadMoreToSearch: "Chargez plus pour rechercher dans les anciennes conversations",
    loadingMore: "Chargement…",
    loadOlderChats: "Charger les conversations plus anciennes",
  },

  // Channels
  channels: {
    title: "Canaux",
    connect: "Connecter",
    modify: "Modifier",
    reconnect: "Reconnecter",
    disconnect: "Déconnecter",
    connected: "Connecté",
    notConnected: "Non connecté",
    pending: "En attente",
    revoked: "Déconnecté",
    disabled: "Désactivé",
    unconfigured: "Non configuré",
    unavailable: "Les connexions aux canaux sont indisponibles pour l'instant.",
    unavailableShort: "Indisponible",
    setupTitle: (name: string) => `Connecter ${name}`,
    setupEditTitle: (name: string) => `Modifier ${name}`,
    setupDescription:
      "Saisissez les valeurs requises par ce processus serveur. Elles ne sont pas écrites dans config.yaml.",
    saveAndConnect: "Enregistrer et connecter",
    saveChanges: "Enregistrer les modifications",
    descriptions: {
      telegram: "Messages directs Telegram via votre bot DeerFlow.",
      slack: "Messages et mentions dans votre espace de travail Slack.",
      discord: "Messages de serveur Discord via votre bot DeerFlow.",
      feishu: "Messages Feishu et Lark via votre application DeerFlow.",
      dingtalk: "Messages DingTalk Stream Push via votre bot DeerFlow.",
      wechat: "Messages WeChat iLink via votre bot DeerFlow.",
      wecom: "Messages WeCom via votre bot IA DeerFlow.",
    },
    connectedAs: (name: string) => `Connecté en tant que ${name}.`,
  },

  // Page titles (document title)
  pages: {
    appName: "DeerFlow",
    chats: "Conversations",
    newChat: "Nouvelle conversation",
    untitled: "Sans titre",
  },

  // Tool calls
  toolCalls: {
    moreSteps: (count: number) => `${count} étape${count === 1 ? "" : "s"} supplémentaire${count === 1 ? "" : "s"}`,
    lessSteps: "Moins d'étapes",
    executeCommand: "Exécuter la commande",
    presentFiles: "Présenter les fichiers",
    needYourHelp: "Besoin de votre aide",
    useTool: (toolName: string) => `Utiliser l'outil « ${toolName} »`,
    searchFor: (query: string) => `Rechercher « ${query} »`,
    searchForRelatedInfo: "Rechercher des informations connexes",
    searchForRelatedImages: "Rechercher des images connexes",
    searchForRelatedImagesFor: (query: string) =>
      `Rechercher des images connexes pour « ${query} »`,
    searchOnWebFor: (query: string) => `Rechercher sur le web « ${query} »`,
    viewWebPage: "Afficher la page web",
    listFolder: "Lister le dossier",
    readFile: "Lire le fichier",
    writeFile: "Écrire le fichier",
    clickToViewContent: "Cliquer pour afficher le contenu du fichier",
    writeTodos: "Mettre à jour la liste des tâches",
    skillInstallTooltip: "Installer la skill et la rendre disponible dans DeerFlow",
  },

  // Uploads
  uploads: {
    uploading: "Téléversement…",
    uploadingFiles: "Téléversement des fichiers, veuillez patienter…",
  },

  subtasks: {
    subtask: "Sous-tâche",
    executing: (count: number) =>
      `Exécution ${count === 1 ? "d'une" : `de ${count}`} sous-tâche${count === 1 ? "" : "s"}${count === 1 ? "" : " en parallèle"}`,
    in_progress: "Sous-tâche en cours",
    completed: "Sous-tâche terminée",
    failed: "Sous-tâche échouée",
  },

  // Token Usage
  tokenUsage: {
    title: "Utilisation des tokens",
    label: "Tokens",
    input: "Entrée",
    output: "Sortie",
    total: "Total",
    view: "Affichage",
    unavailable:
      "Aucune utilisation de tokens pour l'instant. L'utilisation s'affiche uniquement après une réponse de modèle réussie lorsque le fournisseur retourne usage_metadata.",
    unavailableShort: "Aucune utilisation retournée",
    note: "Les totaux de l'en-tête utilisent l'utilisation persistée du thread, plus l'utilisation en cours visible pendant qu'une exécution est toujours en streaming. Les données par tour et de débogage proviennent uniquement des messages actuellement visibles. Les totaux peuvent différer des pages de facturation du fournisseur.",
    presets: {
      off: "Désactivé",
      summary: "Résumé",
      perTurn: "Par tour",
      debug: "Débogage",
    },
    presetDescriptions: {
      off: "Masquer l'utilisation des tokens dans l'en-tête et la conversation.",
      summary: "Afficher uniquement le total de la conversation en cours dans l'en-tête.",
      perTurn:
        "Afficher le total dans l'en-tête et un résumé de tokens par tour de l'assistant.",
      debug: "Afficher le total dans l'en-tête et les détails de débogage des tokens par étape.",
    },
    finalAnswer: "Réponse finale",
    stepTotal: "Total de l'étape",
    sharedAttribution: "Partagé entre plusieurs actions à cette étape",
    subagent: (description: string) => `Sous-agent : ${description}`,
    startTodo: (content: string) => `Démarrer la tâche : ${content}`,
    completeTodo: (content: string) => `Terminer la tâche : ${content}`,
    updateTodo: (content: string) => `Mettre à jour la tâche : ${content}`,
    removeTodo: (content: string) => `Supprimer la tâche : ${content}`,
  },

  // Shortcuts
  shortcuts: {
    searchActions: "Rechercher des actions…",
    noResults: "Aucun résultat trouvé.",
    actions: "Actions",
    keyboardShortcuts: "Raccourcis clavier",
    keyboardShortcutsDescription:
      "Naviguez plus rapidement dans DeerFlow grâce aux raccourcis clavier.",
    openCommandPalette: "Ouvrir la palette de commandes",
    toggleSidebar: "Afficher/masquer la barre latérale",
  },

  // Settings
  settings: {
    title: "Paramètres",
    description: "Ajustez l'apparence et le comportement de DeerFlow selon vos préférences.",
    sections: {
      account: "Compte",
      appearance: "Apparence",
      channels: "Canaux",
      memory: "Mémoire",
      tools: "Outils",
      skills: "Skills",
      notification: "Notifications",
      about: "À propos",
    },
    memory: {
      title: "Mémoire",
      description:
        "DeerFlow apprend automatiquement de vos conversations en arrière-plan. Ces souvenirs aident DeerFlow à mieux vous comprendre et à offrir une expérience plus personnalisée.",
      empty: "Aucune donnée de mémoire à afficher.",
      rawJson: "JSON brut",
      exportButton: "Exporter la mémoire",
      exportSuccess: "Mémoire exportée",
      importButton: "Importer la mémoire",
      importConfirmTitle: "Importer la mémoire ?",
      importConfirmDescription:
        "Ceci remplacera votre mémoire actuelle par la sauvegarde JSON sélectionnée.",
      importFileLabel: "Fichier sélectionné",
      importInvalidFile:
        "Impossible de lire le fichier de mémoire sélectionné. Veuillez choisir un export JSON valide.",
      importSuccess: "Mémoire importée",
      manualFactSource: "Manuel",
      addFact: "Ajouter un fait",
      addFactTitle: "Ajouter un fait en mémoire",
      editFactTitle: "Modifier un fait en mémoire",
      addFactSuccess: "Fait créé",
      editFactSuccess: "Fait mis à jour",
      clearAll: "Effacer toute la mémoire",
      clearAllConfirmTitle: "Effacer toute la mémoire ?",
      clearAllConfirmDescription:
        "Cela supprimera tous les résumés et faits sauvegardés. Cette action est irréversible.",
      clearAllSuccess: "Toute la mémoire a été effacée",
      factDeleteConfirmTitle: "Supprimer ce fait ?",
      factDeleteConfirmDescription:
        "Ce fait sera immédiatement supprimé de la mémoire. Cette action est irréversible.",
      factDeleteSuccess: "Fait supprimé",
      factContentLabel: "Contenu",
      factCategoryLabel: "Catégorie",
      factConfidenceLabel: "Confiance",
      factContentPlaceholder: "Décrivez le fait que vous souhaitez mémoriser",
      factCategoryPlaceholder: "contexte",
      factConfidenceHint: "Utilisez un nombre entre 0 et 1.",
      factSave: "Enregistrer le fait",
      factValidationContent: "Le contenu du fait ne peut pas être vide.",
      factValidationConfidence: "La confiance doit être un nombre entre 0 et 1.",
      noFacts: "Aucun fait enregistré pour l'instant.",
      summaryReadOnly:
        "Les sections de résumé sont en lecture seule pour l'instant. Vous pouvez ajouter, modifier ou supprimer des faits individuels, ou effacer toute la mémoire.",
      memoryFullyEmpty: "Aucun souvenir enregistré pour l'instant.",
      factPreviewLabel: "Fait à supprimer",
      searchPlaceholder: "Rechercher dans la mémoire",
      filterAll: "Tout",
      filterFacts: "Faits",
      filterSummaries: "Résumés",
      noMatches: "Aucun souvenir correspondant trouvé.",
      markdown: {
        overview: "Vue d'ensemble",
        userContext: "Contexte utilisateur",
        work: "Travail",
        personal: "Personnel",
        topOfMind: "Priorités actuelles",
        historyBackground: "Historique",
        recentMonths: "Mois récents",
        earlierContext: "Contexte antérieur",
        longTermBackground: "Contexte à long terme",
        updatedAt: "Mis à jour le",
        facts: "Faits",
        empty: "(vide)",
        table: {
          category: "Catégorie",
          confidence: "Confiance",
          confidenceLevel: {
            veryHigh: "Très élevée",
            high: "Élevée",
            normal: "Normale",
            unknown: "Inconnue",
          },
          content: "Contenu",
          source: "Source",
          createdAt: "Créé le",
          view: "Voir",
        },
      },
    },
    appearance: {
      themeTitle: "Thème",
      themeDescription:
        "Choisissez si l'interface suit votre appareil ou reste fixe.",
      system: "Système",
      light: "Clair",
      dark: "Sombre",
      systemDescription: "Suit automatiquement les préférences du système d'exploitation.",
      lightDescription: "Palette lumineuse avec un contraste élevé pour la journée.",
      darkDescription: "Palette sombre qui réduit l'éblouissement pour la concentration.",
      languageTitle: "Langue",
      languageDescription: "Basculer entre les langues.",
    },
    tools: {
      title: "Outils",
      description: "Gérez la configuration et l'état d'activation des outils MCP.",
      adminRequired: "Des privilèges d'administrateur sont requis pour gérer les outils MCP.",
      empty: "Aucun outil MCP configuré.",
    },
    channels: {
      title: "Canaux",
      description:
        "Connectez des comptes de messagerie instantanée pouvant envoyer des messages à DeerFlow depuis l'extérieur du navigateur.",
      disabled:
        "Les connexions aux canaux ne sont pas activées sur ce serveur. Demandez à un administrateur d'activer channel_connections.",
    },
    skills: {
      title: "Skills de l'agent",
      description:
        "Gérez la configuration et l'état d'activation des skills de l'agent.",
      createSkill: "Créer une skill",
      emptyTitle: "Aucune skill pour l'instant",
      emptyDescription:
        "Placez vos dossiers de skills dans le dossier `/skills/custom` à la racine de DeerFlow.",
      emptyButton: "Créer votre première skill",
    },
    notification: {
      title: "Notifications",
      description:
        "DeerFlow envoie uniquement une notification de fin lorsque la fenêtre n'est pas active. Particulièrement utile pour les tâches longues : vous pouvez passer à autre chose et être averti une fois terminé.",
      requestPermission: "Demander l'autorisation de notification",
      deniedHint:
        "L'autorisation de notification a été refusée. Vous pouvez l'activer dans les paramètres du site de votre navigateur pour recevoir des alertes de fin.",
      testButton: "Envoyer une notification de test",
      testTitle: "DeerFlow",
      testBody: "Ceci est une notification de test.",
      notSupported: "Votre navigateur ne prend pas en charge les notifications.",
      disableNotification: "Désactiver les notifications",
    },
    account: {
      profileTitle: "Profil",
      email: "E-mail",
      role: "Rôle",
      changePasswordTitle: "Changer le mot de passe",
      changePasswordDescription: "Mettez à jour le mot de passe de votre compte.",
      currentPassword: "Mot de passe actuel",
      newPassword: "Nouveau mot de passe",
      confirmNewPassword: "Confirmer le nouveau mot de passe",
      passwordMismatch: "Les nouveaux mots de passe ne correspondent pas",
      passwordTooShort: "Le mot de passe doit contenir au moins 8 caractères",
      passwordChangedSuccess: "Mot de passe modifié avec succès",
      networkError: "Erreur réseau. Veuillez réessayer.",
      updating: "Mise à jour…",
      updatePassword: "Mettre à jour le mot de passe",
      signOut: "Se déconnecter",
    },
    acknowledge: {
      emptyTitle: "Remerciements",
      emptyDescription: "Les crédits et remerciements s'afficheront ici.",
    },
  },
};

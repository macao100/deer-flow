export interface Skill {
  name: string;
  description: string;
  category: "public" | "custom";
  license: string;
  enabled: boolean;
}

export interface CustomSkillContent extends Skill {
  content: string;
}

export interface SkillScanResult {
  decision: "allow" | "warn" | "block";
  reason: string;
}

// ── Catalogue de skills publiques (descriptions enrichies) ─────────────

export interface SkillCatalogEntry {
  name: string;
  description: string;
  icon: string;
  category: "research" | "creation" | "analysis" | "dev" | "design";
}

export const SKILL_CATALOG: SkillCatalogEntry[] = [
  {
    name: "deep-research",
    description: "Recherche web multi-angle avec vérification adverse. Pour toute question nécessitant des sources fiables.",
    icon: "🔍",
    category: "research",
  },
  {
    name: "academic-paper-review",
    description: "Révision académique structurée : méthodes, résultats, biais, qualité des citations.",
    icon: "📄",
    category: "research",
  },
  {
    name: "systematic-literature-review",
    description: "Revue systématique de littérature : recherche exhaustive, synthèse, méta-analyse.",
    icon: "📚",
    category: "research",
  },
  {
    name: "github-deep-research",
    description: "Exploration approfondie de repos GitHub : structure, code, historiques, PRs.",
    icon: "🐙",
    category: "research",
  },
  {
    name: "data-analysis",
    description: "Analyse de données Excel/CSV avec DuckDB : statistiques, SQL, visualisations.",
    icon: "📊",
    category: "analysis",
  },
  {
    name: "consulting-analysis",
    description: "Cadre d'analyse consulting : structuration, hypothèses, recommandations, slides.",
    icon: "📈",
    category: "analysis",
  },
  {
    name: "chart-visualization",
    description: "Création de graphiques et visualisations de données interactives.",
    icon: "📉",
    category: "creation",
  },
  {
    name: "image-generation",
    description: "Génération et édition d'images via IA : prompts détaillés, styles, itérations.",
    icon: "🎨",
    category: "creation",
  },
  {
    name: "frontend-design",
    description: "Design d'interfaces web : composants, mise en page, animations, accessibilité.",
    icon: "🖌️",
    category: "design",
  },
  {
    name: "web-design-guidelines",
    description: "Directives de design web : typographie, couleurs, responsive, accessibilité.",
    icon: "🎯",
    category: "design",
  },
  {
    name: "code-documentation",
    description: "Documentation de code automatique : JSDoc, README, diagrammes d'architecture.",
    icon: "📝",
    category: "dev",
  },
  {
    name: "skill-creator",
    description: "Assistant de création de skills DeerFlow : structure, métadonnées, bonnes pratiques.",
    icon: "🛠️",
    category: "dev",
  },
  {
    name: "ppt-generation",
    description: "Génération de présentations PowerPoint structurées à partir de contenu.",
    icon: "🖼️",
    category: "creation",
  },
  {
    name: "newsletter-generation",
    description: "Création de newsletters : curation, rédaction, mise en page, ton adapté.",
    icon: "📧",
    category: "creation",
  },
  {
    name: "podcast-generation",
    description: "Génération de scripts de podcast : structure, timing, dialogues, narration.",
    icon: "🎙️",
    category: "creation",
  },
  {
    name: "video-generation",
    description: "Création de scripts vidéo : storyboard, narration, timing, visuels.",
    icon: "🎬",
    category: "creation",
  },
  {
    name: "music-generation",
    description: "Composition musicale assistée : styles, structures, instruments, paroles.",
    icon: "🎵",
    category: "creation",
  },
  {
    name: "surprise-me",
    description: "Mode découverte : suggestion aléatoire de skills selon le contexte.",
    icon: "🎲",
    category: "creation",
  },
];

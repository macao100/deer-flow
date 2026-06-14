import type { Locale } from "./locale";
import { enUS, frFR, zhCN, type Translations } from "./locales";

export const translations: Record<Locale, Translations> = {
  "en-US": enUS,
  "fr-FR": frFR,
  "zh-CN": zhCN,
};

import type { Ingredient, IngredientGroup } from "../types/contract";

export const GROUPS: IngredientGroup[] = [
  { id: "heritage", name_ru: "Drevnosti i vera" },
  { id: "industry", name_ru: "Industriya i tekhnika" },
  { id: "nature", name_ru: "Priroda" },
  { id: "culture", name_ru: "Kultura" },
  { id: "food_body", name_ru: "Eda i telo" },
  { id: "shopping", name_ru: "Pokupki" },
  { id: "activity", name_ru: "Aktivnost" },
];

export const INGREDIENTS: Ingredient[] = [
  { id: "ancient_temple", name_ru: "Khramy i monastyri", group: "heritage", density_label: "dense", density_measured: 370 },
  { id: "fortress", name_ru: "Kremli i kreposti", group: "heritage", density_label: "medium", density_measured: 12 },
  { id: "manor", name_ru: "Usadby i dvortsy", group: "heritage", density_label: "rare", density_measured: 8 },
  { id: "archaeology", name_ru: "Arkheologiya i gorodishcha", group: "heritage", density_label: "rare", density_measured: 3 },
  { id: "industrial_museum", name_ru: "Muzei tekhniki i promyshlennosti", group: "industry", density_label: "rare", density_measured: 1 },
  { id: "ruins", name_ru: "Zabroshki i ruiny", group: "industry", density_label: "medium", density_measured: 76 },
  { id: "railway_heritage", name_ru: "Zheleznye dorogi i parovozy", group: "industry", density_label: "rare", density_measured: null },
  { id: "quarry", name_ru: "Shakhty i karery", group: "industry", density_label: null, density_measured: null },
  { id: "viewpoint", name_ru: "Smotrivye i vershiny", group: "nature", density_label: "medium", density_measured: 35 },
  { id: "waterfall", name_ru: "Vodopady i porogi", group: "nature", density_label: "absent_in_region", density_measured: 0 },
  { id: "cave", name_ru: "Peshchery", group: "nature", density_label: "absent_in_region", density_measured: 0 },
  { id: "spring", name_ru: "Istochniki", group: "nature", density_label: "medium", density_measured: 74 },
  { id: "reserve", name_ru: "Zapovedniki i natsparki", group: "nature", density_label: "rare", density_measured: 3 },
  { id: "beach", name_ru: "Ozera i plyazhi", group: "nature", density_label: null, density_measured: null },
  { id: "museum_any", name_ru: "Muzei", group: "culture", density_label: "dense", density_measured: 164 },
  { id: "gallery", name_ru: "Galerei", group: "culture", density_label: null, density_measured: null },
  { id: "theatre", name_ru: "Teatry i kontsertnye zaly", group: "culture", density_label: null, density_measured: null },
  { id: "artwork", name_ru: "Art-obekty i strit-art", group: "culture", density_label: null, density_measured: null },
  { id: "market", name_ru: "Rynki i gastromarkety", group: "food_body", density_label: null, density_measured: null },
  { id: "local_food", name_ru: "Lokalnaya gastronomiya", group: "food_body", density_label: null, density_measured: null },
  { id: "brewery", name_ru: "Vinodelni, pivovarny, syrovarni", group: "food_body", density_label: null, density_measured: null },
  { id: "banya", name_ru: "Bani, termy, spa", group: "food_body", density_label: null, density_measured: null },
  { id: "crafts", name_ru: "Remesla i promysly", group: "shopping", density_label: null, density_measured: null },
  { id: "antiques", name_ru: "Antikvariat i barakholki", group: "shopping", density_label: null, density_measured: null },
  { id: "outlet", name_ru: "Autlety i fabrichnye magaziny", group: "shopping", density_label: null, density_measured: null },
  { id: "ski", name_ru: "Gornolyzhka", group: "activity", density_label: null, density_measured: null },
  { id: "hiking", name_ru: "Trekking i velomarshruty", group: "activity", density_label: null, density_measured: null },
];

export const GROUP_NAME_RU: Record<string, string> = {
  heritage: "Древности и вера",
  industry: "Индустрия и техника",
  nature: "Природа",
  culture: "Культура",
  food_body: "Еда и тело",
  shopping: "Покупки",
  activity: "Активность",
};

export const INGREDIENT_NAME_RU: Record<string, string> = {
  ancient_temple: "Храмы и монастыри",
  fortress: "Кремли и крепости",
  manor: "Усадьбы и дворцы",
  archaeology: "Археология и городища",
  industrial_museum: "Музеи техники и промышленности",
  ruins: "Заброшки и руины",
  railway_heritage: "Железные дороги и паровозы",
  quarry: "Шахты и карьеры",
  viewpoint: "Смотровые и вершины",
  waterfall: "Водопады и пороги",
  cave: "Пещеры",
  spring: "Источники",
  reserve: "Заповедники и нацпарки",
  beach: "Озёра и пляжи",
  museum_any: "Музеи",
  gallery: "Галереи",
  theatre: "Театры и концертные залы",
  artwork: "Арт-объекты и стрит-арт",
  market: "Рынки и гастромаркеты",
  local_food: "Локальная гастрономия",
  brewery: "Винодельни, пивоварни, сыроварни",
  banya: "Бани, термы, спа",
  crafts: "Ремёсла и промыслы",
  antiques: "Антиквариат и барахолки",
  outlet: "Аутлеты и фабричные магазины",
  ski: "Горнолыжка",
  hiking: "Треккинг и веломаршруты",
};

export const INGREDIENT_IDS = new Set(INGREDIENTS.map((item) => item.id));

export function knownIngredients(ids: string[]): string[] {
  const out: string[] = [];
  for (const id of ids) {
    if (!INGREDIENT_IDS.has(id)) continue;
    if (out.includes(id)) continue;
    out.push(id);
  }
  return out;
}

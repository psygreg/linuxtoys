const fs = require('fs').promises;
const fsSync = require('fs');
const path = require('path');

class LinuxToysDataProcessor {
  constructor() {
    this.cacheDir = process.argv[2] ? path.resolve(process.argv[2]) : path.join(process.cwd(), 'cache');
    this.repoDir = process.argv[3] ? path.resolve(process.argv[3]) : path.join(process.cwd(), 'linuxtoys');
    this.categories = {};
    this.translations = {};
  }

  async init() {
    try {
      await fs.access(this.cacheDir);
    } catch {
      await fs.mkdir(this.cacheDir, { recursive: true });
    }

    try {
      await fs.access(this.repoDir);
    } catch {
      throw new Error(`LinuxToys repo not found at: ${this.repoDir}`);
    }
  }

  async readLocalFile(filePath) {
    try {
      return await fs.readFile(path.join(this.repoDir, filePath), 'utf8');
    } catch (error) {
      console.warn(`Could not read file: ${filePath}`, error.message);
      return null;
    }
  }

  async readLocalDir(dirPath) {
    try {
      const fullPath = path.join(this.repoDir, dirPath);
      const entries = await fs.readdir(fullPath, { withFileTypes: true });
      return entries.map(entry => ({
        name: entry.name,
        type: entry.isDirectory() ? 'dir' : 'file',
        path: path.join(dirPath, entry.name)
      }));
    } catch (error) {
      console.warn(`Could not read directory: ${dirPath}`, error.message);
      return [];
    }
  }

  readLocalFileAsJson(filePath) {
    try {
      const content = fsSync.readFileSync(path.join(this.repoDir, filePath), 'utf8');
      return JSON.parse(content);
    } catch {
      return null;
    }
  }

  parseScriptMetadata(scriptContent) {
    const metadata = {
      name: '',
      description: '',
      icon: 'application-x-executable',
      version: '1.0'
    };

    const lines = scriptContent.split('\n');
    for (const line of lines) {
      if (!line.startsWith('#')) break;

      const content = line.substring(1).trim();
      const colonIndex = content.indexOf(':');
      if (colonIndex === -1) continue;

      const key = content.substring(0, colonIndex).trim().toLowerCase();
      const value = content.substring(colonIndex + 1).trim();

      if (key === 'name') metadata.name = value;
      else if (key === 'description') metadata.description = value;
      else if (key === 'icon') metadata.icon = value;
      else if (key === 'version') metadata.version = value;
    }

    return metadata;
  }

  parseCategoryInfo(content) {
    const info = {
      icon: 'folder-open',
      description: 'A category of scripts.',
      mode: 'menu'
    };

    const lines = content.split('\n');
    for (const line of lines) {
      const colonIndex = line.indexOf(':');
      if (colonIndex === -1) continue;

      const key = line.substring(0, colonIndex).trim().toLowerCase();
      const value = line.substring(colonIndex + 1).trim();

      if (key === 'icon') info.icon = value;
      else if (key === 'description') info.description = value;
      else if (key === 'mode') info.mode = value;
      else if (key === 'name') info.name = value;
    }

    return info;
  }

  async loadTranslations() {
    console.log('Loading translations...');
    const supportedLanguages = ['en', 'pt', 'es', 'fr', 'de', 'zh', 'ja', 'ru'];

    for (const lang of supportedLanguages) {
      try {
        const parsed = this.readLocalFileAsJson(`p3/libs/lang/${lang}.json`);
        if (parsed) {
          this.translations[lang] = parsed;
          console.log(`Loaded ${lang} translations: ${Object.keys(parsed).length} keys`);
        }
      } catch (error) {
        console.warn(`Could not load translations for ${lang}:`, error.message);
      }
    }
  }

  resolveTranslation(key, lang = 'en') {
    const translations = this.translations[lang] || this.translations['en'] || {};
    return translations[key] || key;
  }

  get promotedSubcategories() {
    return {
      'utils': { 'privacy': 'privacy' }
    };
  }

  async processScriptsDirectory() {
    console.log('Processing scripts directory...');

    const scriptsDir = await this.readLocalDir('p3/scripts');
    if (!scriptsDir.length) return;

    const excludedDirs = ['edu'];
    for (const item of scriptsDir) {
      if (item.type === 'dir' && !excludedDirs.includes(item.name)) {
        await this.processCategory(item.name, `p3/scripts/${item.name}`);
      }
    }

    for (const [parentName, promotions] of Object.entries(this.promotedSubcategories)) {
      for (const [subName, topLevelKey] of Object.entries(promotions)) {
        await this.processCategory(topLevelKey, `p3/scripts/${parentName}/${subName}`);
      }
    }
  }

  async processCategory(categoryName, categoryPath) {
    console.log(`Processing category: ${categoryName}`);

    const categoryContents = await this.readLocalDir(categoryPath);
    if (!categoryContents.length) return;

    const categoryInfoFile = categoryContents.find(f => f.name === 'category-info.txt');
    let categoryInfo = {
      icon: 'folder-open',
      description: 'A category of scripts.',
      mode: 'menu'
    };

    if (categoryInfoFile) {
      const infoContent = await this.readLocalFile(categoryInfoFile.path);
      if (infoContent) {
        categoryInfo = this.parseCategoryInfo(infoContent);
      }
    }

    this.categories[categoryName] = {
      name: categoryName,
      ...categoryInfo,
      tools: [],
      subcategories: {}
    };

    const flattenedSubcategories = {
      'devs': ['ides'],
      'utils': ['peripherals']
    };
    const toFlatten = flattenedSubcategories[categoryName] || [];
    const toSkip = Object.keys(this.promotedSubcategories[categoryName] || {});

    for (const item of categoryContents) {
      if (item.type === 'file' && item.name.endsWith('.sh')) {
        await this.processScript(categoryName, item.name, item.path);
      } else if (item.type === 'dir' && item.name !== '.git') {
        if (toFlatten.includes(item.name)) {
          await this.flattenSubcategory(categoryName, item.path);
        } else if (toSkip.includes(item.name)) {
          console.log(`Skipping promoted subcategory: ${categoryName}/${item.name}`);
        } else {
          await this.processSubcategory(categoryName, item.name, item.path);
        }
      }
    }
  }

  async flattenSubcategory(parentCategory, subcategoryPath) {
    console.log(`Flattening subcategory into ${parentCategory}: ${subcategoryPath}`);

    const subcategoryContents = await this.readLocalDir(subcategoryPath);
    if (!subcategoryContents.length) return;

    for (const item of subcategoryContents) {
      if (item.type === 'file' && item.name.endsWith('.sh')) {
        await this.processScript(parentCategory, item.name, item.path);
      }
    }
  }

  async processSubcategory(parentCategory, subcategoryName, subcategoryPath) {
    console.log(`Processing subcategory: ${parentCategory}/${subcategoryName}`);

    const subcategoryContents = await this.readLocalDir(subcategoryPath);
    if (!subcategoryContents.length) return;

    const categoryInfoFile = subcategoryContents.find(f => f.name === 'category-info.txt');
    let subcategoryInfo = {
      icon: 'folder-open',
      description: 'A subcategory of scripts.',
      mode: 'menu'
    };

    if (categoryInfoFile) {
      const infoContent = await this.readLocalFile(categoryInfoFile.path);
      if (infoContent) {
        subcategoryInfo = this.parseCategoryInfo(infoContent);
      }
    }

    this.categories[parentCategory].subcategories[subcategoryName] = {
      name: subcategoryName,
      ...subcategoryInfo,
      tools: []
    };

    for (const item of subcategoryContents) {
      if (item.type === 'file' && item.name.endsWith('.sh')) {
        await this.processScript(parentCategory, item.name, item.path, subcategoryName);
      }
    }
  }

  async processScript(categoryName, scriptName, scriptPath, subcategoryName = null) {
    const scriptContent = await this.readLocalFile(scriptPath);
    if (!scriptContent) return;

    const metadata = this.parseScriptMetadata(scriptContent);
    if (!metadata.name) {
      metadata.name = scriptName.replace('.sh', '');
    }

    const tool = {
      name: metadata.name,
      description: metadata.description,
      icon: metadata.icon,
      version: metadata.version,
      scriptPath: scriptPath
    };

    if (subcategoryName) {
      this.categories[categoryName].subcategories[subcategoryName].tools.push(tool);
    } else {
      this.categories[categoryName].tools.push(tool);
    }
  }

  async buildTranslatedCategories() {
    console.log('Building translated categories...');

    const translatedData = {};
    const supportedLanguages = Object.keys(this.translations);

    for (const lang of supportedLanguages) {
      translatedData[lang] = {};

      for (const [categoryKey, categoryData] of Object.entries(this.categories)) {
        const translatedCategory = {
          ...categoryData,
          displayName: this.resolveTranslation(categoryKey, lang),
          description: this.resolveTranslation(categoryData.description, lang),
          tools: categoryData.tools.map(tool => ({
            ...tool,
            name: this.resolveTranslation(tool.name, lang),
            description: this.resolveTranslation(tool.description, lang)
          })),
          subcategories: {}
        };

        for (const [subKey, subData] of Object.entries(categoryData.subcategories)) {
          translatedCategory.subcategories[subKey] = {
            ...subData,
            displayName: this.resolveTranslation(subKey, lang),
            description: this.resolveTranslation(subData.description, lang),
            tools: subData.tools.map(tool => ({
              ...tool,
              name: this.resolveTranslation(tool.name, lang),
              description: this.resolveTranslation(tool.description, lang)
            }))
          };
        }

        translatedData[lang][categoryKey] = translatedCategory;
      }
    }

    return translatedData;
  }

  async saveCache() {
    console.log('Saving cache files...');

    await fs.writeFile(
      path.join(this.cacheDir, 'categories.json'),
      JSON.stringify(this.categories, null, 2)
    );

    await fs.writeFile(
      path.join(this.cacheDir, 'translations.json'),
      JSON.stringify(this.translations, null, 2)
    );

    const translatedData = await this.buildTranslatedCategories();
    await fs.writeFile(
      path.join(this.cacheDir, 'translated-categories.json'),
      JSON.stringify(translatedData, null, 2)
    );

    const summary = {
      lastUpdated: new Date().toISOString(),
      categoryCount: Object.keys(this.categories).length,
      totalTools: Object.values(this.categories).reduce((sum, cat) =>
        sum + cat.tools.length + Object.values(cat.subcategories).reduce((subSum, sub) =>
          subSum + sub.tools.length, 0), 0),
      supportedLanguages: Object.keys(this.translations),
      categories: Object.keys(this.categories)
    };

    await fs.writeFile(
      path.join(this.cacheDir, 'summary.json'),
      JSON.stringify(summary, null, 2)
    );

    console.log(`Cache updated successfully!`);
    console.log(`- ${summary.categoryCount} categories`);
    console.log(`- ${summary.totalTools} total tools`);
    console.log(`- ${summary.supportedLanguages.length} languages`);
  }

  async process() {
    try {
      await this.init();
      console.log(`Reading LinuxToys data from: ${this.repoDir}`);

      await this.loadTranslations();
      await this.processScriptsDirectory();
      await this.saveCache();

      console.log('LinuxToys data processing completed successfully!');
    } catch (error) {
      console.error('Error processing LinuxToys data:', error);
      process.exit(1);
    }
  }
}

const processor = new LinuxToysDataProcessor();
processor.process();

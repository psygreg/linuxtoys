const axios = require('axios');
const fs = require('fs').promises;
const path = require('path');

class LinuxToysDataProcessor {
  constructor() {
    this.baseUrl = 'https://codeberg.org/api/v1/repos/psygreg/linuxtoys';
    this.rawUrl = 'https://codeberg.org/psygreg/linuxtoys/raw/branch/master';
    this.cacheDir = process.argv[2] ? path.resolve(process.argv[2]) : path.join(process.cwd(), 'cache');
    this.categories = {};
    this.translations = {};
    this.tools = {};

    // Add auth token if available
    this.token = process.env.GITHUB_TOKEN;
    this.axiosConfig = this.token ? {
      headers: { 'Authorization': `token ${this.token}` }
    } : {};
  }

  async init() {
    try {
      await fs.access(this.cacheDir);
    } catch {
      await fs.mkdir(this.cacheDir, { recursive: true });
    }
  }

  async fetchLatestRelease() {
    try {
      const response = await axios.get(`${this.baseUrl}/releases/latest`, this.axiosConfig);
      return response.data;
    } catch (error) {
      console.log('Could not fetch latest release, using main branch');
      return null;
    }
  }

  async fetchFileContents(filePath) {
    try {
      const response = await axios.get(`${this.rawUrl}/${filePath}`, this.axiosConfig);
      return response.data;
    } catch (error) {
      console.warn(`Could not fetch file: ${filePath}`, error.message);
      return null;
    }
  }

  async fetchDirectoryListing(dirPath) {
    try {
      const response = await axios.get(`${this.baseUrl}/contents/${dirPath}`, this.axiosConfig);
      return response.data;
    } catch (error) {
      console.warn(`Could not fetch directory: ${dirPath}`, error.message);
      return [];
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
        const content = await this.fetchFileContents(`p3/libs/lang/${lang}.json`);
        if (content) {
          // If content is already an object (axios parsed it), use it directly
          // Otherwise, parse it as JSON string
          if (typeof content === 'object') {
            this.translations[lang] = content;
          } else {
            this.translations[lang] = JSON.parse(content);
          }
          console.log(`Loaded ${lang} translations: ${Object.keys(this.translations[lang]).length} keys`);
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

  async processScriptsDirectory() {
    console.log('Processing scripts directory...');

    const scriptsDir = await this.fetchDirectoryListing('p3/scripts');
    if (!scriptsDir) return;

    // Process category directories
    for (const item of scriptsDir) {
      if (item.type === 'dir') {
        await this.processCategory(item.name, `p3/scripts/${item.name}`);
      }
    }
  }

  async processCategory(categoryName, categoryPath) {
    console.log(`Processing category: ${categoryName}`);

    const categoryContents = await this.fetchDirectoryListing(categoryPath);
    if (!categoryContents) return;

    // Load category info
    const categoryInfoFile = categoryContents.find(f => f.name === 'category-info.txt');
    let categoryInfo = {
      icon: 'folder-open',
      description: 'A category of scripts.',
      mode: 'menu'
    };

    if (categoryInfoFile) {
      const infoContent = await this.fetchFileContents(categoryInfoFile.path);
      if (infoContent) {
        categoryInfo = this.parseCategoryInfo(infoContent);
      }
    }

    // Initialize category
    this.categories[categoryName] = {
      name: categoryName,
      ...categoryInfo,
      tools: [],
      subcategories: {}
    };

    // Process scripts and subcategories
    for (const item of categoryContents) {
      if (item.type === 'file' && item.name.endsWith('.sh')) {
        await this.processScript(categoryName, item.name, item.path);
      } else if (item.type === 'dir' && item.name !== '.git') {
        await this.processSubcategory(categoryName, item.name, item.path);
      }
    }
  }

  async processSubcategory(parentCategory, subcategoryName, subcategoryPath) {
    console.log(`Processing subcategory: ${parentCategory}/${subcategoryName}`);

    const subcategoryContents = await this.fetchDirectoryListing(subcategoryPath);
    if (!subcategoryContents) return;

    // Load subcategory info
    const categoryInfoFile = subcategoryContents.find(f => f.name === 'category-info.txt');
    let subcategoryInfo = {
      icon: 'folder-open',
      description: 'A subcategory of scripts.',
      mode: 'menu'
    };

    if (categoryInfoFile) {
      const infoContent = await this.fetchFileContents(categoryInfoFile.path);
      if (infoContent) {
        subcategoryInfo = this.parseCategoryInfo(infoContent);
      }
    }

    // Initialize subcategory
    this.categories[parentCategory].subcategories[subcategoryName] = {
      name: subcategoryName,
      ...subcategoryInfo,
      tools: []
    };

    // Process scripts in subcategory
    for (const item of subcategoryContents) {
      if (item.type === 'file' && item.name.endsWith('.sh')) {
        await this.processScript(parentCategory, item.name, item.path, subcategoryName);
      }
    }
  }

  async processScript(categoryName, scriptName, scriptPath, subcategoryName = null) {
    const scriptContent = await this.fetchFileContents(scriptPath);
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

    // Add to appropriate category or subcategory
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

        // Translate subcategories
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

    // Save raw categories data
    await fs.writeFile(
      path.join(this.cacheDir, 'categories.json'),
      JSON.stringify(this.categories, null, 2)
    );

    // Save translations
    await fs.writeFile(
      path.join(this.cacheDir, 'translations.json'),
      JSON.stringify(this.translations, null, 2)
    );

    // Build and save translated categories
    const translatedData = await this.buildTranslatedCategories();
    await fs.writeFile(
      path.join(this.cacheDir, 'translated-categories.json'),
      JSON.stringify(translatedData, null, 2)
    );

    // Save summary for easy consumption
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
      console.log('Fetching LinuxToys data...');

      const release = await this.fetchLatestRelease();
      if (release) {
        console.log(`Latest release: ${release.tag_name}`);
      }

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

// Run the processor
const processor = new LinuxToysDataProcessor();
processor.process();

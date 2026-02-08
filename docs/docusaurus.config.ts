import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'AI Quiz Generation Benchmark',
  tagline: 'LLMs as Judges - Evaluating AI-Generated Quizzes',

  future: {
    v4: true,
  },

  // Set the production url of your site here
  url: 'https://ls1intum.github.io',
  baseUrl: '/paper-al-quiz-generation-benchmark/',

  // GitHub pages deployment config
  organizationName: 'ls1',
  projectName: 'paper-al-quiz-generation-benchmark',

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          routeBasePath: '/', // Serve docs at the site's root
          sidebarPath: require.resolve('./sidebars.ts'),
        },
        blog: false, // Disable the blog feature
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    colorMode: {
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'Quiz Benchmark',
      items: [
        {
          to: '/',
          label: 'Home',
          position: 'left',
        },
        {
          type: 'docSidebar',
          sidebarId: 'userManual',
          label: 'User Manual',
          position: 'left',
        },
        {
          type: 'docSidebar',
          sidebarId: 'contributorGuide',
          label: 'Contributor Guide',
          position: 'left',
        },
        {
          href: 'https://github.com/ls1intum/paper-al-quiz-generation-benchmark',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      copyright: `AI Quiz Generation Benchmark © ${new Date().getFullYear()}. Built with Docusaurus.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
    },
  } satisfies Preset.ThemeConfig,
};

export default config;

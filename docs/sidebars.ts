import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  userManual: [
    {
      type: 'category',
      label: 'User Manual',
      items: [
        'user-manual/overview',
        'user-manual/quick-start',
        'user-manual/usage-guide',
        'user-manual/metrics',
        'user-manual/best-practices',
        'user-manual/troubleshooting',
        'user-manual/example-workflows',
        'user-manual/references',
      ],
    },
  ],
  contributorGuide: [
    {
      type: 'category',
      label: 'Contributor Guide',
      items: [
        'contributor-guide/architecture',
        'contributor-guide/customization',
        'contributor-guide/testing',
      ],
    },
  ],
};

export default sidebars;

import { defineConfig } from 'vitepress'

export default defineConfig({
  lang: 'zh-TW',
  title: 'AI Governance Wiki',
  description: 'AI Governance Framework 的工程導覽、導入方法與證據邊界',
  base: '/ai-governance-framework/',
  cleanUrls: true,
  lastUpdated: true,
  sitemap: {
    hostname: 'https://gavin0099.github.io/ai-governance-framework/'
  },
  head: [
    ['meta', { name: 'theme-color', content: '#f4f0e8' }],
    ['meta', { property: 'og:type', content: 'website' }],
    ['meta', { property: 'og:locale', content: 'zh_TW' }],
    ['meta', { property: 'og:title', content: 'AI Governance Wiki' }],
    ['meta', {
      property: 'og:description',
      content: '讓 AI coding agent 的邊界、證據與宣稱可被審核。'
    }]
  ],
  themeConfig: {
    logo: {
      light: '/mark-light.svg',
      dark: '/mark-dark.svg',
      alt: 'AI Governance Wiki'
    },
    siteTitle: 'AI Governance Wiki',
    nav: [
      { text: '概念', link: '/core-concepts' },
      { text: '工作流程', link: '/workflow' },
      { text: '導入', link: '/adoption' },
      { text: '證據', link: '/evidence' },
      { text: 'Repo 狀態', link: '/generated/repository-status' }
    ],
    sidebar: [
      {
        text: '開始',
        items: [
          { text: 'Wiki 首頁', link: '/' },
          { text: '核心概念', link: '/core-concepts' },
          { text: '系統架構', link: '/architecture' }
        ]
      },
      {
        text: '工程使用',
        items: [
          { text: 'Agent 工作流程', link: '/workflow' },
          { text: 'Consumer 導入', link: '/adoption' },
          { text: 'Skills 與工程方法', link: '/skills' }
        ]
      },
      {
        text: '證據與現況',
        items: [
          { text: '證據邊界', link: '/evidence' },
          { text: 'Repository 自動摘要', link: '/generated/repository-status' }
        ]
      }
    ],
    socialLinks: [
      {
        icon: 'github',
        link: 'https://github.com/Gavin0099/ai-governance-framework'
      }
    ],
    editLink: {
      pattern: 'https://github.com/Gavin0099/ai-governance-framework/edit/main/docs/wiki/:path',
      text: '在 GitHub 編輯這一頁'
    },
    search: {
      provider: 'local',
      options: {
        translations: {
          button: {
            buttonText: '搜尋 Wiki',
            buttonAriaLabel: '搜尋 Wiki'
          },
          modal: {
            noResultsText: '找不到相關內容',
            resetButtonTitle: '清除搜尋',
            footer: {
              selectText: '選擇',
              navigateText: '切換',
              closeText: '關閉'
            }
          }
        }
      }
    },
    outline: {
      level: [2, 3],
      label: '本頁內容'
    },
    docFooter: {
      prev: '上一頁',
      next: '下一頁'
    },
    lastUpdated: {
      text: '最後更新'
    },
    footer: {
      message: 'Repository 是內容真相來源；Wiki 是公開、可讀的投影。',
      copyright: 'AI Governance Framework'
    }
  }
})

/**
 * NyayamGPT SEO Wrapper Component
 * ================================
 * Implements react-helmet-async for SEO optimization
 */

import { Helmet } from "react-helmet-async";

interface SEOWrapperProps {
  title?: string;
  description?: string;
  keywords?: string[];
  ogImage?: string;
  ogType?: "website" | "article";
  canonicalUrl?: string;
  article?: boolean;
  publishedTime?: string;
  modifiedTime?: string;
  author?: string;
  noIndex?: boolean;
}

const DEFAULT_TITLE = "NyayamGPT - AI Legal Assistant for Indian Law";
const DEFAULT_DESCRIPTION =
  "Get instant answers to your legal questions about Indian law. NyayamGPT is an AI-powered legal assistant that provides accurate information on IPC, CrPC, Constitution, and more.";
const DEFAULT_KEYWORDS = [
  "Indian law",
  "legal assistant",
  "AI lawyer",
  "IPC sections",
  "CrPC",
  "legal advice India",
  "law chatbot",
  "NyayamGPT",
  "Indian Constitution",
  "legal help",
  "court procedures",
  "bail provisions",
  "consumer rights India",
];
const DEFAULT_OG_IMAGE = "/og-image.png";
const SITE_URL = "https://nyayamgpt.in";

export function SEOWrapper({
  title,
  description = DEFAULT_DESCRIPTION,
  keywords = DEFAULT_KEYWORDS,
  ogImage = DEFAULT_OG_IMAGE,
  ogType = "website",
  canonicalUrl,
  article = false,
  publishedTime,
  modifiedTime,
  author = "NyayamGPT Team",
  noIndex = false,
}: SEOWrapperProps) {
  const fullTitle = title ? `${title} | NyayamGPT` : DEFAULT_TITLE;
  const fullCanonicalUrl = canonicalUrl
    ? `${SITE_URL}${canonicalUrl}`
    : SITE_URL;
  const fullOgImage = ogImage.startsWith("http")
    ? ogImage
    : `${SITE_URL}${ogImage}`;

  // JSON-LD Structured Data
  const webApplicationSchema = {
    "@context": "https://schema.org",
    "@type": "WebApplication",
    name: "NyayamGPT",
    description: DEFAULT_DESCRIPTION,
    url: SITE_URL,
    applicationCategory: "LegalApplication",
    operatingSystem: "Web",
    offers: {
      "@type": "Offer",
      price: "0",
      priceCurrency: "INR",
    },
    creator: {
      "@type": "Organization",
      name: "NyayamGPT",
      url: SITE_URL,
    },
  };

  const organizationSchema = {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: "NyayamGPT",
    url: SITE_URL,
    logo: `${SITE_URL}/logo.png`,
    description: "AI-powered legal information platform for Indian citizens",
    sameAs: [
      "https://twitter.com/nyayamgpt",
      "https://linkedin.com/company/nyayamgpt",
    ],
    contactPoint: {
      "@type": "ContactPoint",
      contactType: "customer service",
      availableLanguage: ["English", "Hindi"],
    },
  };

  const faqSchema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: [
      {
        "@type": "Question",
        name: "What is NyayamGPT?",
        acceptedAnswer: {
          "@type": "Answer",
          text: "NyayamGPT is an AI-powered legal assistant that provides information about Indian law, including IPC sections, CrPC procedures, constitutional rights, and more. It helps citizens understand their legal rights in simple language.",
        },
      },
      {
        "@type": "Question",
        name: "Is NyayamGPT free to use?",
        acceptedAnswer: {
          "@type": "Answer",
          text: "Yes, NyayamGPT is free to use for basic legal information queries. We offer a premium tier with additional features for legal professionals.",
        },
      },
      {
        "@type": "Question",
        name: "Can NyayamGPT replace a lawyer?",
        acceptedAnswer: {
          "@type": "Answer",
          text: "No, NyayamGPT provides legal information, not legal advice. For specific legal matters, you should always consult a qualified lawyer. NyayamGPT helps you understand legal concepts and prepare questions for your lawyer.",
        },
      },
      {
        "@type": "Question",
        name: "What laws does NyayamGPT cover?",
        acceptedAnswer: {
          "@type": "Answer",
          text: "NyayamGPT covers major Indian laws including the Indian Penal Code (IPC), Code of Criminal Procedure (CrPC), Indian Evidence Act, Constitution of India, Motor Vehicle Act, Consumer Protection Act, and many more.",
        },
      },
    ],
  };

  return (
    <Helmet>
      {/* Basic Meta Tags */}
      <title>{fullTitle}</title>
      <meta name='description' content={description} />
      <meta name='keywords' content={keywords.join(", ")} />
      <meta name='author' content={author} />
      <meta name='viewport' content='width=device-width, initial-scale=1.0' />
      <meta charSet='utf-8' />

      {/* Robots */}
      {noIndex ? (
        <meta name='robots' content='noindex, nofollow' />
      ) : (
        <meta
          name='robots'
          content='index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1'
        />
      )}

      {/* Canonical URL */}
      <link rel='canonical' href={fullCanonicalUrl} />

      {/* Language Alternates */}
      <link
        rel='alternate'
        hrefLang='en'
        href={`${SITE_URL}/en${canonicalUrl || ""}`}
      />
      <link
        rel='alternate'
        hrefLang='hi'
        href={`${SITE_URL}/hi${canonicalUrl || ""}`}
      />
      <link rel='alternate' hrefLang='x-default' href={fullCanonicalUrl} />

      {/* Open Graph */}
      <meta property='og:title' content={fullTitle} />
      <meta property='og:description' content={description} />
      <meta property='og:image' content={fullOgImage} />
      <meta property='og:image:width' content='1200' />
      <meta property='og:image:height' content='630' />
      <meta property='og:type' content={article ? "article" : ogType} />
      <meta property='og:url' content={fullCanonicalUrl} />
      <meta property='og:site_name' content='NyayamGPT' />
      <meta property='og:locale' content='en_IN' />
      <meta property='og:locale:alternate' content='hi_IN' />

      {/* Article Specific */}
      {article && publishedTime && (
        <meta property='article:published_time' content={publishedTime} />
      )}
      {article && modifiedTime && (
        <meta property='article:modified_time' content={modifiedTime} />
      )}
      {article && <meta property='article:author' content={author} />}

      {/* Twitter Card */}
      <meta name='twitter:card' content='summary_large_image' />
      <meta name='twitter:site' content='@nyayamgpt' />
      <meta name='twitter:creator' content='@nyayamgpt' />
      <meta name='twitter:title' content={fullTitle} />
      <meta name='twitter:description' content={description} />
      <meta name='twitter:image' content={fullOgImage} />

      {/* Theme Color - Chrome, Edge, Safari */}
      <meta
        name='theme-color'
        content='#d4af37'
        media='(prefers-color-scheme: light)'
      />
      <meta
        name='theme-color'
        content='#18181b'
        media='(prefers-color-scheme: dark)'
      />
      <meta name='msapplication-TileColor' content='#d4af37' />

      {/* Icons */}
      <link
        rel='apple-touch-icon'
        sizes='180x180'
        href='/apple-touch-icon.png'
      />
      <link rel='icon' type='image/svg+xml' href='/favicon.svg' />
      <link
        rel='icon'
        type='image/png'
        sizes='32x32'
        href='/favicon-32x32.png'
      />
      <link
        rel='icon'
        type='image/png'
        sizes='16x16'
        href='/favicon-16x16.png'
      />

      {/* JSON-LD Structured Data */}
      <script type='application/ld+json'>
        {JSON.stringify(webApplicationSchema)}
      </script>
      <script type='application/ld+json'>
        {JSON.stringify(organizationSchema)}
      </script>
      <script type='application/ld+json'>{JSON.stringify(faqSchema)}</script>
    </Helmet>
  );
}

export default SEOWrapper;

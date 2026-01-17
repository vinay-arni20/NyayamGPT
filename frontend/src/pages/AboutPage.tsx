import { Link } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { SEOWrapper } from "../components/layout/SEOWrapper";
import { Scale, Shield, Zap, Globe, BrainCircuit } from "lucide-react";

export default function AboutPage() {
  return (
    <>
      <SEOWrapper
        title='About NyayamGPT - AI Legal Assistant'
        description='Learn about NyayamGPT, the AI-powered legal assistant for Indian law.'
      />
      <div className='min-h-screen bg-background'>
        <header className='border-b bg-card/50 backdrop-blur-sm'>
          <div className='container mx-auto flex h-16 items-center justify-between px-4'>
            <Link
              to='/'
              className='flex items-center gap-2 font-heading text-xl font-bold text-primary'
            >
              <Scale className='h-6 w-6' />
              NyayamGPT
            </Link>
            <div className='flex gap-4'>
              <Link to='/login'>
                <Button variant='ghost'>Login</Button>
              </Link>
              <Link to='/signup'>
                <Button>Get Started</Button>
              </Link>
            </div>
          </div>
        </header>

        <main className='container mx-auto px-4 py-12'>
          <div className='mx-auto max-w-3xl text-center'>
            <h1 className='font-heading text-4xl font-bold text-foreground sm:text-5xl'>
              Democratizing Legal Knowledge
            </h1>
            <p className='mt-6 text-lg text-muted-foreground'>
              NyayamGPT is an advanced AI legal assistant designed to make
              Indian law accessible, understandable, and actionable for
              everyone.
            </p>
          </div>

          <div className='mt-16 grid gap-8 sm:grid-cols-2 lg:grid-cols-3'>
            <FeatureCard
              icon={<Shield className='h-8 w-8 text-blue-500' />}
              title='Accurate & Reliable'
              description='Powered by advanced RAG technology with 11 Indian legal codes including new 2023 Criminal Codes (BNS, BNSS, BSA).'
            />
            <FeatureCard
              icon={<Zap className='h-8 w-8 text-yellow-500' />}
              title='Instant Answers'
              description='Get immediate responses to your legal queries with 3-stage validation and <2% hallucination rate.'
            />
            <FeatureCard
              icon={<Globe className='h-8 w-8 text-green-500' />}
              title='Multilingual Support'
              description='Ask questions in 11 Indian languages and get answers in the language you understand best.'
            />
            <FeatureCard
              icon={<BrainCircuit className='h-8 w-8 text-purple-500' />}
              title='Deep Research'
              description='Complex legal analysis using multi-step reasoning, citation verification, and web search capabilities.'
            />
          </div>
        </main>
      </div>
    </>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className='rounded-xl border bg-card p-6 shadow-sm transition-all hover:shadow-md'>
      <div className='mb-4'>{icon}</div>
      <h3 className='mb-2 font-heading text-xl font-semibold'>{title}</h3>
      <p className='text-muted-foreground'>{description}</p>
    </div>
  );
}

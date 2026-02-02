'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    router.push('/dashboard');
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-background">
      <div className="text-center">
        <div className="flex justify-center mb-4">
          <div className="w-12 h-12 rounded-lg bg-primary flex items-center justify-center">
            <Loader2 className="w-6 h-6 text-primary-foreground animate-spin" />
          </div>
        </div>
        <p className="text-muted-foreground">Loading KnowHub...</p>
      </div>
    </div>
  );
}

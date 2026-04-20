import React from 'react';

interface BrandingSectionProps {
    title: string;
    subtitle: string;
    heading: string;
    description: string;
    features: Array<{ icon: string; title: string; subtitle: string }>;
}

export const BrandingSection: React.FC<BrandingSectionProps> = ({
    title,
    subtitle,
    heading,
    description,
    features,
}) => {
    return (
        <div className="hidden lg:flex lg:w-1/2 flex-col justify-center px-12 py-20 bg-blue-100">
            <div className="space-y-8 max-w-lg">
                {/* Header */}
                <div>
                    <div className="flex items-center gap-2 mb-4">
                        <span className="text-3xl">🧠</span>
                        <h1 className="text-xl font-bold text-gray-800">{title}</h1>
                    </div>
                    <p className="text-gray-600 text-base">{subtitle}</p>
                </div>

                {/* Main Heading */}
                <div className="space-y-4">
                    <h2 className="text-4xl font-bold leading-tight text-gray-900">
                        {heading.split(' ').map((word, idx) =>
                            word.includes('trị') || word.includes('tuệ') || word.includes('số') ?
                                <span key={idx} className="text-amber-600">{word} </span> :
                                <span key={idx}>{word} </span>
                        )}
                    </h2>
                    <p className="text-gray-700 text-sm leading-relaxed">{description}</p>
                </div>

                {/* Features */}
                <div className="space-y-4 mt-8">
                    {features.map((feature, index) => (
                        <div key={index} className="bg-white rounded-lg p-4 border-l-4 border-amber-600">
                            <p className="font-bold text-gray-900 text-sm">{feature.title}</p>
                            <p className="text-gray-600 text-xs mt-1">{feature.subtitle}</p>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

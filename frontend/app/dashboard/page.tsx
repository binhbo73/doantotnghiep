'use client';

import React, { useState, useRef, useEffect } from 'react';
import { DashboardLayout } from '@/components/dashboard-layout';
import { Message } from '@/components/message';
import { ChatInput } from '@/components/chat-input';
import { Skeleton } from '@/components/ui/skeleton';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: { document: string; page: number; snippet: string }[];
  timestamp: Date;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Hello! I\'m your AI Knowledge Manager. I can help you find information from your organization\'s documents, answer policy questions, and assist with training materials. What would you like to know?',
      sources: [],
      timestamp: new Date(Date.now() - 3600000),
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = (message: string) => {
    // Add user message
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: message,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    // Simulate AI response with streaming effect
    setTimeout(() => {
      const aiMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `I found relevant information in your documents. Based on the query "${message}", here are some helpful details and insights.`,
        sources: [
          {
            document: 'HR_Policy.pdf',
            page: 12,
            snippet:
              'Employees are entitled to 20 days of paid leave per year, in addition to 10 public holidays.',
          },
          {
            document: 'Employee_Handbook.docx',
            page: 5,
            snippet:
              'All benefits inquiries should be directed to the HR department during business hours.',
          },
        ],
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, aiMessage]);
      setIsLoading(false);
    }, 1500);
  };

  return (
    <DashboardLayout>
      <div className="flex flex-col h-[calc(100vh-12rem)] md:h-[calc(100vh-10rem)] max-w-4xl mx-auto w-full">
        {/* Messages Container */}
        <div className="flex-1 overflow-y-auto space-y-4 px-2 md:px-4 py-4 md:py-6">
          {messages.map((msg) => (
            <Message
              key={msg.id}
              role={msg.role}
              content={msg.content}
              sources={msg.sources}
              timestamp={msg.timestamp}
            />
          ))}

          {/* Thinking Animation */}
          {isLoading && (
            <div className="flex gap-3 mb-4">
              <div className="w-8 h-8 rounded-full bg-sidebar-primary/20 flex items-center justify-center flex-shrink-0 flex-none" />
              <div className="space-y-2 flex-1">
                <Skeleton className="h-4 w-48" />
                <Skeleton className="h-4 w-64" />
                <Skeleton className="h-4 w-56" />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Chat Input */}
        <ChatInput onSend={handleSendMessage} isLoading={isLoading} />
      </div>
    </DashboardLayout>
  );
}

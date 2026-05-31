"use client";

import { useState, useRef, useEffect } from "react";
import { Button, TextInput, Title, Text } from "@tremor/react";
import { Send, Loader2 } from "lucide-react";
import ChatMessage from "@/components/ChatMessage";
import { sendChatMessage } from "@/lib/api";
import type { ChatMessage as ChatMessageType } from "@/lib/types";

export default function ChatDashboard() {
  const [messages, setMessages] = useState<ChatMessageType[]>([
    {
      role: "assistant",
      content:
        "Hi! I'm your expense intelligence assistant. Ask me anything about your company's spending — for example:\n\n- What did Operations spend on fuel?\n- Show me spending by department\n- What are the top permit fees this month?\n- Compare spending across transaction types",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    const query = input.trim();
    if (!query || loading) return;

    setInput("");
    setLoading(true);

    const userMessage: ChatMessageType = { role: "user", content: query };
    setMessages((prev) => [...prev, userMessage]);

    try {
      // Pass the existing conversation_id to maintain context
      const response = await sendChatMessage(query, conversationId || undefined);

      // Save the conversation_id for follow-up questions
      if (response.conversation_id) {
        setConversationId(response.conversation_id);
      }

      const assistantResponse: ChatMessageType = {
        role: "assistant",
        content: response,
      };

      setMessages((prev) => [...prev, assistantResponse]);
    } catch (error) {
      const errorMessage: ChatMessageType = {
        role: "assistant",
        content: `Sorry, I encountered an error: ${error}. Please try rephrasing your question.`,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewConversation = () => {
    setConversationId(null);
    setMessages([
      {
        role: "assistant",
        content:
          "Hi! I'm your expense intelligence assistant. Ask me anything about your company's spending.",
      },
    ]);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] max-w-5xl mx-auto w-full px-4">
      <div className="flex items-center justify-between py-4 border-b border-gray-200 dark:border-gray-700">
        <div>
          <Title>Talk to Your Data</Title>
          <Text>Ask questions about your company spending in plain English</Text>
        </div>
        {conversationId && (
          <Button variant="secondary" size="xs" onClick={handleNewConversation}>
            New Conversation
          </Button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto py-4 space-y-4">
        {messages.map((msg, i) => (
          <ChatMessage key={i} message={msg} />
        ))}

        {loading && (
          <div className="flex items-center gap-2 text-gray-500 pl-10">
            <Loader2 className="h-4 w-4 animate-spin" />
            <Text>Thinking...</Text>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="py-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex gap-2">
          <TextInput
            placeholder="Ask about your expenses..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            className="flex-1"
          />
          <Button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            icon={Send}
          >
            Send
          </Button>
        </div>
      </div>
    </div>
  );
}

"use client";

import { Card, Text } from "@tremor/react";
import { Bot, User } from "lucide-react";
import VisualBubble from "./VisualBubble";
import type { ChatMessage as ChatMessageType, ChatResponse } from "@/lib/types";

interface ChatMessageProps {
  message: ChatMessageType;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
          isUser ? "bg-blue-600" : "bg-gray-700"
        }`}
      >
        {isUser ? (
          <User className="h-4 w-4 text-white" />
        ) : (
          <Bot className="h-4 w-4 text-white" />
        )}
      </div>

      <div
        className={`max-w-[80%] rounded-lg px-4 py-2 ${
          isUser
            ? "bg-blue-600 text-white"
            : "bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100"
        }`}
      >
        {isUser ? (
          <Text>{String(message.content)}</Text>
        ) : typeof message.content === "string" ? (
          <Text>{message.content}</Text>
        ) : (
          <AssistantContent response={message.content as ChatResponse} />
        )}
      </div>
    </div>
  );
}

function AssistantContent({ response }: { response: ChatResponse }) {
  return (
    <div className="space-y-2">
      {response.explanation && (
        <p className="whitespace-pre-wrap text-sm">{response.explanation}</p>
      )}

      {response.visualization_type !== "text" &&
        response.data &&
        response.data.length > 0 && (
          <VisualBubble
            visualizationType={response.visualization_type}
            config={response.config}
            data={response.data}
          />
        )}
    </div>
  );
}

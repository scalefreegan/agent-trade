/**
 * API hooks for the Conversation feature.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchApi, postApi, patchApi, deleteApi } from './client';
import type {
  ConversationDetail,
  ConversationListResponse,
  ConversationMessage,
} from './types';

export function useConversations() {
  return useQuery({
    queryKey: ['conversations'],
    queryFn: () => fetchApi<ConversationListResponse>('/conversations'),
  });
}

// Exponential backoff intervals for polling while a response is in progress.
// Starts at 1s, doubles each step, caps at 8s.
// This reduces server load for long-running Claude invocations.
const POLL_INTERVALS_MS = [1000, 2000, 4000, 8000];
const MAX_POLL_INTERVAL_MS = POLL_INTERVALS_MS[POLL_INTERVALS_MS.length - 1];

export function useConversation(conversationId: string | null) {
  return useQuery({
    queryKey: ['conversation', conversationId],
    queryFn: () =>
      fetchApi<ConversationDetail>(`/conversations/${conversationId}`),
    enabled: !!conversationId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status !== 'responding') return false;

      // Use the number of successful fetches while responding to pick the
      // backoff tier, so the interval grows the longer we wait.
      const fetchCount = query.state.dataUpdateCount ?? 0;
      return POLL_INTERVALS_MS[Math.min(fetchCount, POLL_INTERVALS_MS.length - 1)] ?? MAX_POLL_INTERVAL_MS;
    },
  });
}

export function useCreateConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (title?: string) =>
      postApi<ConversationDetail>('/conversations', { title }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });
}

export function useSendMessage(conversationId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (content: string) => {
      if (!conversationId) {
        return Promise.reject(new Error('No conversation selected'));
      }
      return postApi<ConversationMessage>(
        `/conversations/${conversationId}/messages`,
        { content }
      );
    },
    onMutate: async (content: string) => {
      if (!conversationId) return;

      await queryClient.cancelQueries({
        queryKey: ['conversation', conversationId],
      });

      const previous = queryClient.getQueryData<ConversationDetail>([
        'conversation',
        conversationId,
      ]);

      if (previous) {
        const optimisticMessage: ConversationMessage = {
          id: `optimistic-${Date.now()}`,
          role: 'user',
          content,
          timestamp: new Date().toISOString(),
        };

        queryClient.setQueryData<ConversationDetail>(
          ['conversation', conversationId],
          {
            ...previous,
            messages: [...previous.messages, optimisticMessage],
            status: 'responding',
          },
        );
      }

      return { previous };
    },
    onError: (_err, _content, context) => {
      if (context?.previous && conversationId) {
        queryClient.setQueryData(
          ['conversation', conversationId],
          context.previous,
        );
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ['conversation', conversationId],
      });
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });
}

export function useUpdateConversationTitle(conversationId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (title: string) => {
      if (!conversationId) {
        return Promise.reject(new Error('No conversation selected'));
      }
      return patchApi<ConversationDetail>(`/conversations/${conversationId}`, {
        title,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['conversation', conversationId],
      });
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });
}

export function useDeleteConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (conversationId: string) =>
      deleteApi(`/conversations/${conversationId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });
}

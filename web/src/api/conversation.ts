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

export function useConversation(conversationId: string | null) {
  return useQuery({
    queryKey: ['conversation', conversationId],
    queryFn: () =>
      fetchApi<ConversationDetail>(`/conversations/${conversationId}`),
    enabled: !!conversationId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'responding' ? 1000 : false;
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
    onSuccess: () => {
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

/**
 * Members List Screen - Searchable member directory
 * Requirements: 3.1, 3.2, 3.8
 */

import React, { useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TextInput,
  TouchableOpacity,
  Image,
  RefreshControl,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useMembersStore } from '../../stores/membersStore';
import { Member } from '../../types/models';
import { MembersStackParamList } from '../../types/navigation';

type MembersNavigationProp = NativeStackNavigationProp<MembersStackParamList, 'MembersList'>;

/**
 * Member list item component
 */
const MemberListItem: React.FC<{
  member: Member;
  onPress: () => void;
}> = ({ member, onPress }) => {
  const fullName = `${member.firstName} ${member.lastName}`;
  const initials = `${member.firstName.charAt(0)}${member.lastName.charAt(0)}`.toUpperCase();

  return (
    <TouchableOpacity style={styles.memberItem} onPress={onPress} activeOpacity={0.7}>
      <View style={styles.avatarContainer}>
        {member.photo ? (
          <Image source={{ uri: member.photo }} style={styles.avatar} />
        ) : (
          <View style={styles.avatarPlaceholder}>
            <Text style={styles.avatarInitials}>{initials}</Text>
          </View>
        )}
      </View>
      <View style={styles.memberInfo}>
        <Text style={styles.memberName}>{fullName}</Text>
        {member.phone && (
          <Text style={styles.memberContact}>
            <Ionicons name="call-outline" size={12} color="#666" /> {member.phone}
          </Text>
        )}
        {member.email && (
          <Text style={styles.memberContact} numberOfLines={1}>
            <Ionicons name="mail-outline" size={12} color="#666" /> {member.email}
          </Text>
        )}
      </View>
      <Ionicons name="chevron-forward" size={20} color="#ccc" />
    </TouchableOpacity>
  );
};

/**
 * Offline indicator banner
 * Requirements: 3.8
 */
const OfflineBanner: React.FC<{ message: string }> = ({ message }) => (
  <View style={styles.offlineBanner}>
    <Ionicons name="cloud-offline-outline" size={16} color="#fff" />
    <Text style={styles.offlineText}>{message}</Text>
  </View>
);

/**
 * Empty state component
 */
const EmptyState: React.FC<{ searchQuery: string }> = ({ searchQuery }) => (
  <View style={styles.emptyState}>
    <Ionicons name="people-outline" size={64} color="#ccc" />
    <Text style={styles.emptyTitle}>
      {searchQuery ? 'Aucun résultat' : 'Aucun membre'}
    </Text>
    <Text style={styles.emptySubtitle}>
      {searchQuery
        ? `Aucun membre ne correspond à "${searchQuery}"`
        : 'La liste des membres est vide'}
    </Text>
  </View>
);

/**
 * Main MembersListScreen component
 * Requirements: 3.1, 3.2, 3.8
 */
export const MembersListScreen: React.FC = () => {
  const navigation = useNavigation<MembersNavigationProp>();
  const {
    filteredMembers,
    searchQuery,
    isLoading,
    isRefreshing,
    error,
    fetchMembers,
    setSearchQuery,
    refreshMembers,
  } = useMembersStore();

  // Fetch members on mount
  useEffect(() => {
    fetchMembers();
  }, [fetchMembers]);

  // Handle member press - navigate to detail
  const handleMemberPress = useCallback(
    (memberId: number) => {
      navigation.navigate('MemberDetail', { memberId });
    },
    [navigation]
  );

  // Handle pull-to-refresh
  const handleRefresh = useCallback(() => {
    refreshMembers();
  }, [refreshMembers]);

  // Render member item
  const renderMemberItem = useCallback(
    ({ item }: { item: Member }) => (
      <MemberListItem
        member={item}
        onPress={() => handleMemberPress(item.id)}
      />
    ),
    [handleMemberPress]
  );

  // Key extractor for FlatList
  const keyExtractor = useCallback((item: Member) => item.id.toString(), []);

  // Show loading state on initial load
  if (isLoading && filteredMembers.length === 0) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#3498db" />
        <Text style={styles.loadingText}>Chargement des membres...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Offline indicator - Requirements: 3.8 */}
      {error && error.includes('hors ligne') && (
        <OfflineBanner message={error} />
      )}

      {/* Search bar - Requirements: 3.2 */}
      <View style={styles.searchContainer}>
        <Ionicons name="search" size={20} color="#999" style={styles.searchIcon} />
        <TextInput
          style={styles.searchInput}
          placeholder="Rechercher un membre..."
          placeholderTextColor="#999"
          value={searchQuery}
          onChangeText={setSearchQuery}
          autoCapitalize="none"
          autoCorrect={false}
          clearButtonMode="while-editing"
        />
        {searchQuery.length > 0 && (
          <TouchableOpacity onPress={() => setSearchQuery('')} style={styles.clearButton}>
            <Ionicons name="close-circle" size={20} color="#999" />
          </TouchableOpacity>
        )}
      </View>

      {/* Results count */}
      <View style={styles.resultsHeader}>
        <Text style={styles.resultsCount}>
          {filteredMembers.length} membre{filteredMembers.length !== 1 ? 's' : ''}
          {searchQuery ? ` pour "${searchQuery}"` : ''}
        </Text>
      </View>

      {/* Members list - Requirements: 3.1 */}
      <FlatList
        data={filteredMembers}
        renderItem={renderMemberItem}
        keyExtractor={keyExtractor}
        contentContainerStyle={
          filteredMembers.length === 0 ? styles.emptyListContainer : styles.listContainer
        }
        refreshControl={
          <RefreshControl
            refreshing={isRefreshing}
            onRefresh={handleRefresh}
            colors={['#3498db']}
            tintColor="#3498db"
          />
        }
        ListEmptyComponent={<EmptyState searchQuery={searchQuery} />}
        showsVerticalScrollIndicator={false}
        initialNumToRender={15}
        maxToRenderPerBatch={10}
        windowSize={5}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f5f5f5',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: '#666',
  },
  offlineBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#e67e22',
    paddingVertical: 8,
    paddingHorizontal: 16,
  },
  offlineText: {
    color: '#fff',
    fontSize: 14,
    marginLeft: 8,
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    margin: 12,
    paddingHorizontal: 12,
    borderRadius: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  searchIcon: {
    marginRight: 8,
  },
  searchInput: {
    flex: 1,
    height: 44,
    fontSize: 16,
    color: '#333',
  },
  clearButton: {
    padding: 4,
  },
  resultsHeader: {
    paddingHorizontal: 16,
    paddingBottom: 8,
  },
  resultsCount: {
    fontSize: 14,
    color: '#666',
  },
  listContainer: {
    paddingHorizontal: 12,
    paddingBottom: 20,
  },
  emptyListContainer: {
    flex: 1,
  },
  memberItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    padding: 12,
    marginBottom: 8,
    borderRadius: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 1,
  },
  avatarContainer: {
    marginRight: 12,
  },
  avatar: {
    width: 50,
    height: 50,
    borderRadius: 25,
  },
  avatarPlaceholder: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: '#3498db',
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarInitials: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  memberInfo: {
    flex: 1,
  },
  memberName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  memberContact: {
    fontSize: 13,
    color: '#666',
    marginBottom: 2,
  },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 32,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginTop: 16,
    marginBottom: 8,
  },
  emptySubtitle: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
  },
});

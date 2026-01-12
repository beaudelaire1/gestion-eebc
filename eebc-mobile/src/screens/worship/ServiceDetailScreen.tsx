/**
 * Service Detail Screen - Full team roster, songs, and confirmation
 * Requirements: 5.3, 5.4, 5.5
 */

import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { RouteProp, useRoute, useNavigation } from '@react-navigation/native';
import { useWorshipStore } from '../../stores/worshipStore';
import { WorshipService, ServiceAssignment, Song } from '../../types/worship';

type ServiceDetailRouteProp = RouteProp<
  { ServiceDetail: { serviceId: number } },
  'ServiceDetail'
>;

export const ServiceDetailScreen: React.FC = () => {
  const route = useRoute<ServiceDetailRouteProp>();
  const navigation = useNavigation();
  const { serviceId } = route.params;

  const {
    getServiceById,
    isLoading,
    error,
    fetchServices,
    confirmAssignment,
    declineAssignment,
  } = useWorshipStore();

  const [service, setService] = useState<WorshipService | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    loadService();
  }, [serviceId]);

  const loadService = async () => {
    const foundService = getServiceById(serviceId);
    if (foundService) {
      setService(foundService);
    } else {
      // Try to fetch services if not found locally
      await fetchServices();
      const refetchedService = getServiceById(serviceId);
      if (refetchedService) {
        setService(refetchedService);
      }
    }
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await fetchServices(true);
    await loadService();
    setIsRefreshing(false);
  };

  const handleConfirmAssignment = async (assignmentId: number) => {
    const result = await confirmAssignment(assignmentId);
    if (result.success) {
      Alert.alert('Confirmé', 'Votre participation a été confirmée.');
      await loadService(); // Refresh service data
    } else {
      Alert.alert('Erreur', result.error || 'Impossible de confirmer la participation.');
    }
  };

  const handleDeclineAssignment = (assignmentId: number) => {
    Alert.prompt(
      'Décliner la participation',
      'Veuillez indiquer la raison de votre indisponibilité:',
      [
        { text: 'Annuler', style: 'cancel' },
        {
          text: 'Décliner',
          style: 'destructive',
          onPress: async (reason) => {
            if (reason) {
              const result = await declineAssignment(assignmentId, reason);
              if (result.success) {
                Alert.alert('Décliné', 'Votre indisponibilité a été enregistrée.');
                await loadService(); // Refresh service data
              } else {
                Alert.alert('Erreur', result.error || 'Impossible de décliner la participation.');
              }
            }
          },
        },
      ],
      'plain-text'
    );
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const formatTime = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('fr-FR', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const groupAssignmentsByCategory = (assignments: ServiceAssignment[]) => {
    const grouped: Record<string, ServiceAssignment[]> = {};
    
    assignments.forEach((assignment) => {
      const category = assignment.role.category;
      if (!grouped[category]) {
        grouped[category] = [];
      }
      grouped[category].push(assignment);
    });

    return grouped;
  };

  const getCategoryTitle = (category: string): string => {
    switch (category) {
      case 'music':
        return 'Musique';
      case 'tech':
        return 'Technique';
      case 'liturgy':
        return 'Liturgie';
      default:
        return category;
    }
  };

  const renderAssignmentItem = (assignment: ServiceAssignment) => {
    const isCurrentUser = assignment.isCurrentUser;

    return (
      <View
        key={assignment.id}
        style={[
          styles.assignmentItem,
          isCurrentUser && styles.currentUserAssignment,
        ]}
      >
        <View style={styles.assignmentInfo}>
          <Text style={styles.assignmentRole}>{assignment.role.name}</Text>
          <Text style={styles.assignmentMember}>
            {assignment.member.firstName} {assignment.member.lastName}
            {isCurrentUser && ' (Vous)'}
          </Text>
        </View>

        <View style={styles.assignmentStatusContainer}>
          <Text
            style={[
              styles.assignmentStatus,
              assignment.status === 'confirmed' && styles.statusConfirmed,
              assignment.status === 'declined' && styles.statusDeclined,
              assignment.status === 'pending' && styles.statusPending,
            ]}
          >
            {assignment.status === 'confirmed' && 'Confirmé'}
            {assignment.status === 'declined' && 'Décliné'}
            {assignment.status === 'pending' && 'En attente'}
          </Text>

          {isCurrentUser && assignment.status === 'pending' && (
            <View style={styles.assignmentActions}>
              <TouchableOpacity
                style={[styles.actionButton, styles.confirmButton]}
                onPress={() => handleConfirmAssignment(assignment.id)}
              >
                <Text style={styles.confirmButtonText}>Confirmer</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.actionButton, styles.declineButton]}
                onPress={() => handleDeclineAssignment(assignment.id)}
              >
                <Text style={styles.declineButtonText}>Décliner</Text>
              </TouchableOpacity>
            </View>
          )}
        </View>
      </View>
    );
  };

  const renderSongItem = (song: Song) => (
    <View key={song.id} style={styles.songItem}>
      <View style={styles.songInfo}>
        <Text style={styles.songTitle}>{song.title}</Text>
        {song.author && <Text style={styles.songAuthor}>par {song.author}</Text>}
      </View>
      {song.key && (
        <View style={styles.songKeyContainer}>
          <Text style={styles.songKey}>{song.key}</Text>
        </View>
      )}
    </View>
  );

  if (isLoading && !service) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Chargement du service...</Text>
      </View>
    );
  }

  if (!service) {
    return (
      <View style={styles.errorContainer}>
        <Text style={styles.errorText}>Service non trouvé</Text>
        <TouchableOpacity
          style={styles.retryButton}
          onPress={() => navigation.goBack()}
        >
          <Text style={styles.retryButtonText}>Retour</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const groupedAssignments = groupAssignmentsByCategory(service.assignments);
  const sortedSongs = [...service.songs].sort((a, b) => a.order - b.order);

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={isRefreshing} onRefresh={handleRefresh} />
      }
    >
      {error && (
        <View style={styles.errorBanner}>
          <Text style={styles.errorBannerText}>{error}</Text>
        </View>
      )}

      {/* Service Header */}
      <View style={styles.header}>
        <Text style={styles.serviceDate}>{formatDate(service.date)}</Text>
        <Text style={styles.serviceTime}>{formatTime(service.date)}</Text>
        <Text style={styles.serviceType}>{service.serviceType}</Text>
        {service.theme && <Text style={styles.serviceTheme}>{service.theme}</Text>}
        {service.preacher && (
          <Text style={styles.servicePreacher}>Prédicateur: {service.preacher}</Text>
        )}
        <Text
          style={[
            styles.serviceStatus,
            service.status === 'confirmed' && styles.statusConfirmed,
            service.status === 'planned' && styles.statusPending,
            service.status === 'completed' && styles.statusCompleted,
          ]}
        >
          {service.status === 'confirmed' && 'Service confirmé'}
          {service.status === 'planned' && 'Service planifié'}
          {service.status === 'completed' && 'Service terminé'}
        </Text>
      </View>

      {/* Team Roster */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Équipe du service</Text>
        {Object.entries(groupedAssignments).map(([category, assignments]) => (
          <View key={category} style={styles.categorySection}>
            <Text style={styles.categoryTitle}>{getCategoryTitle(category)}</Text>
            {assignments.map(renderAssignmentItem)}
          </View>
        ))}
        {service.assignments.length === 0 && (
          <Text style={styles.emptyText}>Aucune assignation pour ce service</Text>
        )}
      </View>

      {/* Songs List */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Chants du service</Text>
        {sortedSongs.map(renderSongItem)}
        {sortedSongs.length === 0 && (
          <Text style={styles.emptyText}>Aucun chant programmé</Text>
        )}
      </View>
    </ScrollView>
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
    marginTop: 16,
    fontSize: 16,
    color: '#666',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f5f5f5',
    padding: 32,
  },
  errorText: {
    fontSize: 18,
    color: '#666',
    textAlign: 'center',
    marginBottom: 24,
  },
  retryButton: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  retryButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  errorBanner: {
    backgroundColor: '#ffebee',
    padding: 12,
    borderLeftWidth: 4,
    borderLeftColor: '#f44336',
  },
  errorBannerText: {
    color: '#c62828',
    fontSize: 14,
  },
  header: {
    backgroundColor: '#fff',
    padding: 20,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  serviceDate: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  serviceTime: {
    fontSize: 16,
    color: '#666',
    marginBottom: 8,
  },
  serviceType: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#007AFF',
    marginBottom: 8,
  },
  serviceTheme: {
    fontSize: 16,
    color: '#666',
    fontStyle: 'italic',
    marginBottom: 8,
  },
  servicePreacher: {
    fontSize: 16,
    color: '#666',
    marginBottom: 12,
  },
  serviceStatus: {
    fontSize: 14,
    fontWeight: '500',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    alignSelf: 'flex-start',
  },
  statusConfirmed: {
    backgroundColor: '#e8f5e8',
    color: '#2e7d32',
  },
  statusDeclined: {
    backgroundColor: '#ffebee',
    color: '#c62828',
  },
  statusPending: {
    backgroundColor: '#fff3e0',
    color: '#ef6c00',
  },
  statusCompleted: {
    backgroundColor: '#e3f2fd',
    color: '#1976d2',
  },
  section: {
    backgroundColor: '#fff',
    marginBottom: 16,
    paddingVertical: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 16,
    paddingHorizontal: 20,
  },
  categorySection: {
    marginBottom: 20,
  },
  categoryTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#007AFF',
    marginBottom: 12,
    paddingHorizontal: 20,
  },
  assignmentItem: {
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  currentUserAssignment: {
    backgroundColor: '#f8f9ff',
    borderLeftWidth: 4,
    borderLeftColor: '#007AFF',
  },
  assignmentInfo: {
    marginBottom: 8,
  },
  assignmentRole: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  assignmentMember: {
    fontSize: 14,
    color: '#666',
  },
  assignmentStatusContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  assignmentStatus: {
    fontSize: 13,
    fontWeight: '500',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  assignmentActions: {
    flexDirection: 'row',
    gap: 8,
  },
  actionButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
  },
  confirmButton: {
    backgroundColor: '#4caf50',
  },
  confirmButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 12,
  },
  declineButton: {
    backgroundColor: '#f44336',
  },
  declineButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 12,
  },
  songItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  songInfo: {
    flex: 1,
  },
  songTitle: {
    fontSize: 16,
    fontWeight: '500',
    color: '#333',
    marginBottom: 2,
  },
  songAuthor: {
    fontSize: 13,
    color: '#666',
  },
  songKeyContainer: {
    backgroundColor: '#e3f2fd',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  songKey: {
    fontSize: 12,
    fontWeight: '600',
    color: '#1976d2',
  },
  emptyText: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    fontStyle: 'italic',
    paddingHorizontal: 20,
  },
});
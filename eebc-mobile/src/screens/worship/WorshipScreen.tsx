/**
 * Worship Screen - List of worship services and user assignments
 * Requirements: 5.1, 5.2, 5.7
 */

import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  RefreshControl,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import { useWorshipStore } from '../../stores/worshipStore';
import { WorshipService, ServiceAssignment } from '../../types/worship';
import { WorshipStackParamList } from '../../navigation/WorshipStack';

type WorshipScreenNavigationProp = StackNavigationProp<
  WorshipStackParamList,
  'WorshipList'
>;

type TabType = 'upcoming' | 'my-assignments' | 'history';

export const WorshipScreen: React.FC = () => {
  const navigation = useNavigation<WorshipScreenNavigationProp>();
  const {
    services,
    myAssignments,
    isLoading,
    isRefreshing,
    error,
    fetchServices,
    refreshServices,
    getUpcomingServices,
    getMyUpcomingAssignments,
    confirmAssignment,
    declineAssignment,
  } = useWorshipStore();

  const [activeTab, setActiveTab] = useState<TabType>('upcoming');

  useEffect(() => {
    fetchServices();
  }, [fetchServices]);

  const handleServicePress = (serviceId: number) => {
    navigation.navigate('ServiceDetail', { serviceId });
  };

  const handleRefresh = async () => {
    await refreshServices();
  };

  const handleConfirmAssignment = async (assignmentId: number) => {
    const result = await confirmAssignment(assignmentId);
    if (result.success) {
      Alert.alert('Confirmé', 'Votre participation a été confirmée.');
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

  const getServicesForTab = (): WorshipService[] => {
    switch (activeTab) {
      case 'upcoming':
        return getUpcomingServices();
      case 'my-assignments':
        return getUpcomingServices().filter(service =>
          service.assignments.some(assignment => assignment.isCurrentUser)
        );
      case 'history':
        const now = new Date();
        const threeMonthsAgo = new Date();
        threeMonthsAgo.setMonth(now.getMonth() - 3);
        
        return services
          .filter(service => {
            const serviceDate = new Date(service.date);
            return serviceDate < now && serviceDate >= threeMonthsAgo;
          })
          .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
      default:
        return [];
    }
  };

  const renderServiceItem = ({ item }: { item: WorshipService }) => {
    const userAssignments = item.assignments.filter(assignment => assignment.isCurrentUser);
    const hasUserAssignment = userAssignments.length > 0;

    return (
      <TouchableOpacity
        style={[styles.serviceCard, hasUserAssignment && styles.serviceCardHighlighted]}
        onPress={() => handleServicePress(item.id)}
        activeOpacity={0.7}
      >
        <View style={styles.serviceHeader}>
          <Text style={styles.serviceDate}>{formatDate(item.date)}</Text>
          <Text style={styles.serviceTime}>{formatTime(item.date)}</Text>
        </View>
        
        <Text style={styles.serviceType}>{item.serviceType}</Text>
        {item.theme && <Text style={styles.serviceTheme}>{item.theme}</Text>}
        {item.preacher && (
          <Text style={styles.servicePreacher}>Prédicateur: {item.preacher}</Text>
        )}

        {hasUserAssignment && (
          <View style={styles.assignmentsSection}>
            <Text style={styles.assignmentsTitle}>Mes rôles:</Text>
            {userAssignments.map((assignment) => (
              <View key={assignment.id} style={styles.assignmentItem}>
                <View style={styles.assignmentInfo}>
                  <Text style={styles.assignmentRole}>{assignment.role.name}</Text>
                  <Text style={[
                    styles.assignmentStatus,
                    assignment.status === 'confirmed' && styles.statusConfirmed,
                    assignment.status === 'declined' && styles.statusDeclined,
                    assignment.status === 'pending' && styles.statusPending,
                  ]}>
                    {assignment.status === 'confirmed' && 'Confirmé'}
                    {assignment.status === 'declined' && 'Décliné'}
                    {assignment.status === 'pending' && 'En attente'}
                  </Text>
                </View>
                
                {assignment.status === 'pending' && activeTab !== 'history' && (
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
            ))}
          </View>
        )}

        <View style={styles.serviceFooter}>
          <Text style={styles.assignmentCount}>
            {item.assignments.length} rôle{item.assignments.length > 1 ? 's' : ''} assigné{item.assignments.length > 1 ? 's' : ''}
          </Text>
          <Text style={[
            styles.serviceStatus,
            item.status === 'confirmed' && styles.statusConfirmed,
            item.status === 'planned' && styles.statusPending,
            item.status === 'completed' && styles.statusCompleted,
          ]}>
            {item.status === 'confirmed' && 'Confirmé'}
            {item.status === 'planned' && 'Planifié'}
            {item.status === 'completed' && 'Terminé'}
          </Text>
        </View>
      </TouchableOpacity>
    );
  };

  const renderEmptyState = () => {
    let message = '';
    switch (activeTab) {
      case 'upcoming':
        message = 'Aucun service à venir';
        break;
      case 'my-assignments':
        message = 'Aucune assignation à venir';
        break;
      case 'history':
        message = 'Aucun historique disponible';
        break;
    }

    return (
      <View style={styles.emptyState}>
        <Text style={styles.emptyStateText}>{message}</Text>
      </View>
    );
  };

  if (isLoading && services.length === 0) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Chargement des services...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {error && (
        <View style={styles.errorBanner}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      )}

      <View style={styles.tabContainer}>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'upcoming' && styles.activeTab]}
          onPress={() => setActiveTab('upcoming')}
        >
          <Text style={[styles.tabText, activeTab === 'upcoming' && styles.activeTabText]}>
            À venir
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'my-assignments' && styles.activeTab]}
          onPress={() => setActiveTab('my-assignments')}
        >
          <Text style={[styles.tabText, activeTab === 'my-assignments' && styles.activeTabText]}>
            Mes rôles
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'history' && styles.activeTab]}
          onPress={() => setActiveTab('history')}
        >
          <Text style={[styles.tabText, activeTab === 'history' && styles.activeTabText]}>
            Historique
          </Text>
        </TouchableOpacity>
      </View>

      <FlatList
        data={getServicesForTab()}
        renderItem={renderServiceItem}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={styles.listContainer}
        refreshControl={
          <RefreshControl refreshing={isRefreshing} onRefresh={handleRefresh} />
        }
        ListEmptyComponent={renderEmptyState}
        showsVerticalScrollIndicator={false}
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
    marginTop: 16,
    fontSize: 16,
    color: '#666',
  },
  errorBanner: {
    backgroundColor: '#ffebee',
    padding: 12,
    borderLeftWidth: 4,
    borderLeftColor: '#f44336',
  },
  errorText: {
    color: '#c62828',
    fontSize: 14,
  },
  tabContainer: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  tab: {
    flex: 1,
    paddingVertical: 16,
    alignItems: 'center',
  },
  activeTab: {
    borderBottomWidth: 2,
    borderBottomColor: '#007AFF',
  },
  tabText: {
    fontSize: 16,
    color: '#666',
  },
  activeTabText: {
    color: '#007AFF',
    fontWeight: '600',
  },
  listContainer: {
    padding: 16,
  },
  serviceCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  serviceCardHighlighted: {
    borderLeftWidth: 4,
    borderLeftColor: '#007AFF',
    backgroundColor: '#f8f9ff',
  },
  serviceHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  serviceDate: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    flex: 1,
  },
  serviceTime: {
    fontSize: 14,
    color: '#666',
  },
  serviceType: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#007AFF',
    marginBottom: 4,
  },
  serviceTheme: {
    fontSize: 14,
    color: '#666',
    fontStyle: 'italic',
    marginBottom: 4,
  },
  servicePreacher: {
    fontSize: 14,
    color: '#666',
    marginBottom: 8,
  },
  assignmentsSection: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  assignmentsTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  assignmentItem: {
    marginBottom: 8,
  },
  assignmentInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  assignmentRole: {
    fontSize: 15,
    fontWeight: '500',
    color: '#333',
  },
  assignmentStatus: {
    fontSize: 13,
    fontWeight: '500',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
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
  assignmentActions: {
    flexDirection: 'row',
    gap: 8,
  },
  actionButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
    flex: 1,
    alignItems: 'center',
  },
  confirmButton: {
    backgroundColor: '#4caf50',
  },
  confirmButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 14,
  },
  declineButton: {
    backgroundColor: '#f44336',
  },
  declineButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 14,
  },
  serviceFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  assignmentCount: {
    fontSize: 13,
    color: '#666',
  },
  serviceStatus: {
    fontSize: 13,
    fontWeight: '500',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 64,
  },
  emptyStateText: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
  },
});

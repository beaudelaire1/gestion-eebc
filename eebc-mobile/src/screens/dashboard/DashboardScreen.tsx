/**
 * Dashboard Screen - Personalized dashboard with role-based widgets
 * Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7
 */

import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useAuthStore } from '../../stores/authStore';
import { useEventsStore } from '../../stores/eventsStore';
import { useAnnouncementsStore } from '../../stores/announcementsStore';
import { useWorshipStore } from '../../stores/worshipStore';
import type { Event } from '../../types/models';
import type { Announcement } from '../../types/announcements';
import type { ServiceAssignment } from '../../types/worship';

interface DashboardWidget {
  id: string;
  title: string;
  content: React.ReactNode;
  onPress?: () => void;
  visible: boolean;
}

export const DashboardScreen: React.FC = () => {
  const navigation = useNavigation();
  const { user } = useAuthStore();
  const {
    fetchEvents,
    getEventsForDate,
    isLoading: eventsLoading,
    error: eventsError,
  } = useEventsStore();
  const {
    fetchAnnouncements,
    sortedAnnouncements,
    unreadCount,
    isLoading: announcementsLoading,
    error: announcementsError,
  } = useAnnouncementsStore();
  const {
    fetchServices,
    getMyUpcomingAssignments,
    isLoading: worshipLoading,
    error: worshipError,
  } = useWorshipStore();

  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      await Promise.all([
        fetchEvents(),
        fetchAnnouncements(),
        fetchServices(),
      ]);
    } catch (error) {
      console.error('Error loading dashboard data:', error);
    }
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await Promise.all([
        fetchEvents(true),
        fetchAnnouncements(true),
        fetchServices(true),
      ]);
    } catch (error) {
      console.error('Error refreshing dashboard:', error);
    } finally {
      setIsRefreshing(false);
    }
  };

  // Get upcoming events for the next 7 days
  const getUpcomingEvents = (): Event[] => {
    const now = new Date();
    const nextWeek = new Date();
    nextWeek.setDate(now.getDate() + 7);

    const events: Event[] = [];
    for (let d = new Date(now); d <= nextWeek; d.setDate(d.getDate() + 1)) {
      const dateStr = d.toISOString().split('T')[0];
      const dayEvents = getEventsForDate(dateStr);
      events.push(...dayEvents);
    }

    return events.slice(0, 3); // Show max 3 events
  };

  // Get recent announcements preview
  const getRecentAnnouncements = (): Announcement[] => {
    return sortedAnnouncements.slice(0, 2); // Show max 2 announcements
  };

  // Get user's upcoming assignments
  const getUpcomingAssignments = (): ServiceAssignment[] => {
    return getMyUpcomingAssignments().slice(0, 2); // Show max 2 assignments
  };

  // Role-based widget visibility
  const isAdmin = user?.role === 'admin';
  const isPastor = user?.role === 'pastor';
  const isSecretary = user?.role === 'secretary';
  const isLeader = user?.role === 'leader';
  const isMember = user?.role === 'member';

  // Quick action buttons based on role
  const getQuickActions = () => {
    const actions = [];

    if (isAdmin || isPastor || isSecretary) {
      actions.push({
        title: 'Membres',
        onPress: () => navigation.navigate('Members' as never),
        color: '#4CAF50',
      });
    }

    if (isAdmin || isPastor || isLeader) {
      actions.push({
        title: 'Événements',
        onPress: () => navigation.navigate('Events' as never),
        color: '#2196F3',
      });
    }

    actions.push({
      title: 'Annonces',
      onPress: () => navigation.navigate('More', { screen: 'Announcements' } as never),
      color: '#FF9800',
    });

    if (isAdmin || isPastor || isLeader) {
      actions.push({
        title: 'Culte',
        onPress: () => navigation.navigate('Worship' as never),
        color: '#9C27B0',
      });
    }

    return actions;
  };

  const widgets: DashboardWidget[] = [
    // Welcome widget - visible to all
    {
      id: 'welcome',
      title: 'Bienvenue',
      visible: true,
      content: (
        <View style={styles.welcomeContent}>
          <Text style={styles.welcomeText}>
            Bonjour {user?.firstName || 'Membre'} !
          </Text>
          <Text style={styles.welcomeSubtext}>
            Bienvenue sur EEBC Mobile
          </Text>
        </View>
      ),
    },

    // Upcoming events widget - visible to all
    {
      id: 'events',
      title: 'Événements à venir',
      visible: true,
      onPress: () => navigation.navigate('Events' as never),
      content: (
        <View style={styles.widgetContent}>
          {eventsLoading ? (
            <Text style={styles.loadingText}>Chargement...</Text>
          ) : eventsError ? (
            <Text style={styles.errorText}>Erreur: {eventsError}</Text>
          ) : (
            <>
              {getUpcomingEvents().map((event) => (
                <View key={event.id} style={styles.eventItem}>
                  <Text style={styles.eventTitle} numberOfLines={1}>
                    {event.title}
                  </Text>
                  <Text style={styles.eventDate}>
                    {new Date(event.startDate).toLocaleDateString('fr-FR', {
                      weekday: 'short',
                      day: 'numeric',
                      month: 'short',
                    })}
                  </Text>
                </View>
              ))}
              {getUpcomingEvents().length === 0 && (
                <Text style={styles.emptyText}>Aucun événement à venir</Text>
              )}
            </>
          )}
        </View>
      ),
    },

    // Announcements widget - visible to all
    {
      id: 'announcements',
      title: `Annonces${unreadCount > 0 ? ` (${unreadCount})` : ''}`,
      visible: true,
      onPress: () => navigation.navigate('More', { screen: 'Announcements' } as never),
      content: (
        <View style={styles.widgetContent}>
          {announcementsLoading ? (
            <Text style={styles.loadingText}>Chargement...</Text>
          ) : announcementsError ? (
            <Text style={styles.errorText}>Erreur: {announcementsError}</Text>
          ) : (
            <>
              {getRecentAnnouncements().map((announcement) => (
                <View key={announcement.id} style={styles.announcementItem}>
                  <View style={styles.announcementHeader}>
                    <Text style={styles.announcementTitle} numberOfLines={1}>
                      {announcement.title}
                    </Text>
                    {announcement.isPinned && (
                      <Text style={styles.pinnedBadge}>📌</Text>
                    )}
                    {!announcement.isRead && (
                      <View style={styles.unreadDot} />
                    )}
                  </View>
                  <Text style={styles.announcementExcerpt} numberOfLines={2}>
                    {announcement.excerpt}
                  </Text>
                </View>
              ))}
              {getRecentAnnouncements().length === 0 && (
                <Text style={styles.emptyText}>Aucune annonce récente</Text>
              )}
            </>
          )}
        </View>
      ),
    },

    // Worship assignments widget - visible to worship team members
    {
      id: 'worship',
      title: 'Mes assignments',
      visible: isAdmin || isPastor || isLeader || (user?.permissions?.includes('worship.view_assignment') ?? false),
      onPress: () => navigation.navigate('Worship' as never),
      content: (
        <View style={styles.widgetContent}>
          {worshipLoading ? (
            <Text style={styles.loadingText}>Chargement...</Text>
          ) : worshipError ? (
            <Text style={styles.errorText}>Erreur: {worshipError}</Text>
          ) : (
            <>
              {getUpcomingAssignments().map((assignment) => (
                <View key={assignment.id} style={styles.assignmentItem}>
                  <Text style={styles.assignmentRole} numberOfLines={1}>
                    {assignment.role.name}
                  </Text>
                  <View style={styles.assignmentStatus}>
                    <Text
                      style={[
                        styles.statusText,
                        assignment.status === 'confirmed' && styles.confirmedStatus,
                        assignment.status === 'pending' && styles.pendingStatus,
                        assignment.status === 'declined' && styles.declinedStatus,
                      ]}
                    >
                      {assignment.status === 'confirmed' && '✓ Confirmé'}
                      {assignment.status === 'pending' && '⏳ En attente'}
                      {assignment.status === 'declined' && '✗ Refusé'}
                    </Text>
                  </View>
                </View>
              ))}
              {getUpcomingAssignments().length === 0 && (
                <Text style={styles.emptyText}>Aucune assignment à venir</Text>
              )}
            </>
          )}
        </View>
      ),
    },

    // BibleClub widget - visible to parents
    {
      id: 'bibleclub',
      title: 'École du dimanche',
      visible: user?.permissions?.includes('bibleclub.view_child') ?? false,
      content: (
        <View style={styles.widgetContent}>
          <Text style={styles.emptyText}>
            Résumé de présence des enfants
          </Text>
          {/* TODO: Implement BibleClub attendance summary */}
        </View>
      ),
    },
  ];

  const visibleWidgets = widgets.filter((widget) => widget.visible);
  const quickActions = getQuickActions();

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={isRefreshing} onRefresh={handleRefresh} />
      }
    >
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Tableau de bord</Text>
        <Text style={styles.headerSubtitle}>
          {new Date().toLocaleDateString('fr-FR', {
            weekday: 'long',
            day: 'numeric',
            month: 'long',
          })}
        </Text>
      </View>

      {/* Quick Actions */}
      {quickActions.length > 0 && (
        <View style={styles.quickActionsContainer}>
          <Text style={styles.sectionTitle}>Actions rapides</Text>
          <View style={styles.quickActions}>
            {quickActions.map((action, index) => (
              <TouchableOpacity
                key={index}
                style={[styles.quickActionButton, { backgroundColor: action.color }]}
                onPress={action.onPress}
              >
                <Text style={styles.quickActionText}>{action.title}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      )}

      {/* Widgets */}
      {visibleWidgets.map((widget) => (
        <TouchableOpacity
          key={widget.id}
          style={styles.widget}
          onPress={widget.onPress}
          disabled={!widget.onPress}
        >
          <View style={styles.widgetHeader}>
            <Text style={styles.widgetTitle}>{widget.title}</Text>
            {widget.onPress && (
              <Text style={styles.widgetArrow}>›</Text>
            )}
          </View>
          {widget.content}
        </TouchableOpacity>
      ))}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    backgroundColor: '#fff',
    padding: 20,
    paddingTop: 60,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 4,
  },
  headerSubtitle: {
    fontSize: 16,
    color: '#666',
  },
  quickActionsContainer: {
    backgroundColor: '#fff',
    margin: 16,
    padding: 16,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 12,
  },
  quickActions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  quickActionButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    minWidth: 80,
    alignItems: 'center',
  },
  quickActionText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '500',
  },
  widget: {
    backgroundColor: '#fff',
    margin: 16,
    marginTop: 0,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  widgetHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    paddingBottom: 8,
  },
  widgetTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
  },
  widgetArrow: {
    fontSize: 24,
    color: '#999',
  },
  widgetContent: {
    paddingHorizontal: 16,
    paddingBottom: 16,
  },
  welcomeContent: {
    alignItems: 'center',
    paddingVertical: 20,
  },
  welcomeText: {
    fontSize: 20,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  welcomeSubtext: {
    fontSize: 16,
    color: '#666',
  },
  eventItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  eventTitle: {
    flex: 1,
    fontSize: 16,
    color: '#333',
  },
  eventDate: {
    fontSize: 14,
    color: '#666',
    marginLeft: 8,
  },
  announcementItem: {
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  announcementHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  announcementTitle: {
    flex: 1,
    fontSize: 16,
    fontWeight: '500',
    color: '#333',
  },
  pinnedBadge: {
    fontSize: 12,
    marginLeft: 8,
  },
  unreadDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#2196F3',
    marginLeft: 8,
  },
  announcementExcerpt: {
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
  },
  assignmentItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  assignmentRole: {
    flex: 1,
    fontSize: 16,
    color: '#333',
  },
  assignmentStatus: {
    marginLeft: 8,
  },
  statusText: {
    fontSize: 14,
    fontWeight: '500',
  },
  confirmedStatus: {
    color: '#4CAF50',
  },
  pendingStatus: {
    color: '#FF9800',
  },
  declinedStatus: {
    color: '#F44336',
  },
  loadingText: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    paddingVertical: 20,
  },
  errorText: {
    fontSize: 14,
    color: '#F44336',
    textAlign: 'center',
    paddingVertical: 20,
  },
  emptyText: {
    fontSize: 14,
    color: '#999',
    textAlign: 'center',
    paddingVertical: 20,
    fontStyle: 'italic',
  },
});

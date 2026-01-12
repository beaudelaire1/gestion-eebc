/**
 * Event Detail Screen - Display event details with registration
 * Requirements: 4.3, 4.4, 4.5, 4.8
 */

import React, { useEffect, useCallback, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  Linking,
  Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRoute, useNavigation, RouteProp } from '@react-navigation/native';
import { useEventsStore } from '../../stores/eventsStore';
import { EventsStackParamList } from '../../types/navigation';
import { eventReminderService } from '../../services/EventReminderService';

type EventDetailRouteProp = RouteProp<EventsStackParamList, 'EventDetail'>;

/**
 * Format date for display
 */
const formatDate = (dateStr: string): string => {
  const date = new Date(dateStr);
  return date.toLocaleDateString('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
};

/**
 * Format time for display
 */
const formatTime = (dateStr: string): string => {
  const date = new Date(dateStr);
  return date.toLocaleTimeString('fr-FR', {
    hour: '2-digit',
    minute: '2-digit',
  });
};

/**
 * Check if event is in the past
 */
const isEventPast = (endDate: string): boolean => {
  return new Date(endDate) < new Date();
};

/**
 * Check if event is full
 */
const isEventFull = (currentParticipants: number, maxParticipants?: number): boolean => {
  if (!maxParticipants) return false;
  return currentParticipants >= maxParticipants;
};

/**
 * Info Row Component
 */
const InfoRow: React.FC<{
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  value: string;
  onPress?: () => void;
}> = ({ icon, label, value, onPress }) => {
  const content = (
    <View style={styles.infoRow}>
      <View style={styles.infoIconContainer}>
        <Ionicons name={icon} size={20} color="#3498db" />
      </View>
      <View style={styles.infoContent}>
        <Text style={styles.infoLabel}>{label}</Text>
        <Text style={[styles.infoValue, onPress && styles.infoValueLink]}>{value}</Text>
      </View>
      {onPress && <Ionicons name="chevron-forward" size={20} color="#ccc" />}
    </View>
  );

  if (onPress) {
    return (
      <TouchableOpacity onPress={onPress} activeOpacity={0.7}>
        {content}
      </TouchableOpacity>
    );
  }

  return content;
};

/**
 * Main EventDetailScreen component
 * Requirements: 4.3, 4.4, 4.5, 4.8
 */
export const EventDetailScreen: React.FC = () => {
  const route = useRoute<EventDetailRouteProp>();
  const navigation = useNavigation();
  const { eventId } = route.params;
  
  const { getEventById, registerForEvent, cancelRegistration } = useEventsStore();
  const [isRegistering, setIsRegistering] = useState(false);
  
  const event = getEventById(eventId);

  // Set navigation title
  useEffect(() => {
    if (event) {
      navigation.setOptions({ title: event.title });
    }
  }, [event, navigation]);

  // Handle registration - Requirements: 4.4, 4.5
  const handleRegister = useCallback(async () => {
    if (!event) return;

    setIsRegistering(true);
    const success = await registerForEvent(eventId);
    setIsRegistering(false);

    if (success) {
      // Schedule reminder notification 24h before - Requirements: 4.6
      await eventReminderService.scheduleReminder(event);

      Alert.alert(
        'Inscription confirmée',
        `Vous êtes inscrit(e) à "${event.title}"`,
        [{ text: 'OK' }]
      );
    } else {
      Alert.alert(
        'Erreur',
        'Impossible de vous inscrire à cet événement. Veuillez réessayer.',
        [{ text: 'OK' }]
      );
    }
  }, [event, eventId, registerForEvent]);

  // Handle cancel registration
  const handleCancelRegistration = useCallback(async () => {
    if (!event) return;

    Alert.alert(
      'Annuler l\'inscription',
      `Voulez-vous vraiment annuler votre inscription à "${event.title}" ?`,
      [
        { text: 'Non', style: 'cancel' },
        {
          text: 'Oui, annuler',
          style: 'destructive',
          onPress: async () => {
            setIsRegistering(true);
            const success = await cancelRegistration(eventId);
            setIsRegistering(false);

            if (success) {
              // Cancel the reminder notification - Requirements: 4.6
              await eventReminderService.cancelReminder(eventId);

              Alert.alert(
                'Inscription annulée',
                'Votre inscription a été annulée.',
                [{ text: 'OK' }]
              );
            } else {
              Alert.alert(
                'Erreur',
                'Impossible d\'annuler votre inscription. Veuillez réessayer.',
                [{ text: 'OK' }]
              );
            }
          },
        },
      ]
    );
  }, [event, eventId, cancelRegistration]);

  // Handle open location in maps
  const handleOpenLocation = useCallback(() => {
    if (!event?.location) return;

    const encodedLocation = encodeURIComponent(event.location);
    const url = Platform.select({
      ios: `maps:0,0?q=${encodedLocation}`,
      android: `geo:0,0?q=${encodedLocation}`,
    });

    if (url) {
      Linking.openURL(url).catch(() => {
        // Fallback to Google Maps web
        Linking.openURL(`https://www.google.com/maps/search/?api=1&query=${encodedLocation}`);
      });
    }
  }, [event?.location]);

  // Handle add to calendar - Requirements: 4.7
  const handleAddToCalendar = useCallback(() => {
    if (!event) return;

    // For now, show an alert - full calendar integration would require expo-calendar
    Alert.alert(
      'Ajouter au calendrier',
      'Cette fonctionnalité sera disponible prochainement.',
      [{ text: 'OK' }]
    );
  }, [event]);

  // Show loading if event not found
  if (!event) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#3498db" />
        <Text style={styles.loadingText}>Chargement...</Text>
      </View>
    );
  }

  const isPast = isEventPast(event.endDate);
  const isFull = isEventFull(event.currentParticipants, event.maxParticipants);
  const canRegister = event.allowsRegistration && !isPast && !isFull && !event.isUserRegistered;
  const canCancel = event.isUserRegistered && !isPast;

  return (
    <View style={styles.container}>
      <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
        {/* Header with badges - Requirements: 4.8 */}
        <View style={styles.header}>
          <View style={styles.badgesRow}>
            <View style={[styles.badge, styles.typeBadge]}>
              <Text style={styles.badgeText}>{event.eventType}</Text>
            </View>
            {event.isUserRegistered && (
              <View style={[styles.badge, styles.registeredBadge]}>
                <Ionicons name="checkmark-circle" size={14} color="#fff" />
                <Text style={[styles.badgeText, styles.registeredBadgeText]}>Inscrit</Text>
              </View>
            )}
            {isPast && (
              <View style={[styles.badge, styles.pastBadge]}>
                <Text style={styles.badgeText}>Terminé</Text>
              </View>
            )}
            {isFull && !isPast && (
              <View style={[styles.badge, styles.fullBadge]}>
                <Text style={styles.badgeText}>Complet</Text>
              </View>
            )}
          </View>
          <Text style={styles.title}>{event.title}</Text>
        </View>

        {/* Event details - Requirements: 4.3 */}
        <View style={styles.detailsCard}>
          <InfoRow
            icon="calendar-outline"
            label="Date"
            value={formatDate(event.startDate)}
          />
          <View style={styles.divider} />
          <InfoRow
            icon="time-outline"
            label="Horaire"
            value={`${formatTime(event.startDate)} - ${formatTime(event.endDate)}`}
          />
          {event.location && (
            <>
              <View style={styles.divider} />
              <InfoRow
                icon="location-outline"
                label="Lieu"
                value={event.location}
                onPress={handleOpenLocation}
              />
            </>
          )}
          {event.allowsRegistration && (
            <>
              <View style={styles.divider} />
              <InfoRow
                icon="people-outline"
                label="Participants"
                value={
                  event.maxParticipants
                    ? `${event.currentParticipants} / ${event.maxParticipants}`
                    : `${event.currentParticipants} inscrit(s)`
                }
              />
            </>
          )}
          {event.isRecurring && (
            <>
              <View style={styles.divider} />
              <InfoRow
                icon="repeat-outline"
                label="Récurrence"
                value="Événement récurrent"
              />
            </>
          )}
        </View>

        {/* Description */}
        {event.description && (
          <View style={styles.descriptionCard}>
            <Text style={styles.sectionTitle}>Description</Text>
            <Text style={styles.description}>{event.description}</Text>
          </View>
        )}

        {/* Actions */}
        <View style={styles.actionsCard}>
          <TouchableOpacity
            style={styles.actionButton}
            onPress={handleAddToCalendar}
            activeOpacity={0.7}
          >
            <Ionicons name="calendar-outline" size={20} color="#3498db" />
            <Text style={styles.actionButtonText}>Ajouter au calendrier</Text>
          </TouchableOpacity>
        </View>

        {/* Spacer for bottom button */}
        <View style={styles.bottomSpacer} />
      </ScrollView>

      {/* Registration button - Requirements: 4.4, 4.5 */}
      {event.allowsRegistration && !isPast && (
        <View style={styles.bottomButtonContainer}>
          {canRegister && (
            <TouchableOpacity
              style={[styles.registerButton, isRegistering && styles.registerButtonDisabled]}
              onPress={handleRegister}
              disabled={isRegistering}
              activeOpacity={0.8}
            >
              {isRegistering ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <>
                  <Ionicons name="add-circle-outline" size={20} color="#fff" />
                  <Text style={styles.registerButtonText}>S'inscrire</Text>
                </>
              )}
            </TouchableOpacity>
          )}
          {canCancel && (
            <TouchableOpacity
              style={[styles.cancelButton, isRegistering && styles.registerButtonDisabled]}
              onPress={handleCancelRegistration}
              disabled={isRegistering}
              activeOpacity={0.8}
            >
              {isRegistering ? (
                <ActivityIndicator size="small" color="#e74c3c" />
              ) : (
                <>
                  <Ionicons name="close-circle-outline" size={20} color="#e74c3c" />
                  <Text style={styles.cancelButtonText}>Annuler l'inscription</Text>
                </>
              )}
            </TouchableOpacity>
          )}
          {isFull && !event.isUserRegistered && (
            <View style={styles.fullMessage}>
              <Ionicons name="information-circle-outline" size={20} color="#e67e22" />
              <Text style={styles.fullMessageText}>
                Cet événement est complet
              </Text>
            </View>
          )}
        </View>
      )}
    </View>
  );
};


const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  scrollView: {
    flex: 1,
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
  // Header
  header: {
    backgroundColor: '#fff',
    padding: 16,
    marginBottom: 12,
  },
  badgesRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 12,
  },
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    marginRight: 8,
    marginBottom: 4,
  },
  typeBadge: {
    backgroundColor: '#ecf0f1',
  },
  registeredBadge: {
    backgroundColor: '#27ae60',
  },
  registeredBadgeText: {
    color: '#fff',
    marginLeft: 4,
  },
  pastBadge: {
    backgroundColor: '#95a5a6',
  },
  fullBadge: {
    backgroundColor: '#e67e22',
  },
  badgeText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#666',
    textTransform: 'capitalize',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  // Details card
  detailsCard: {
    backgroundColor: '#fff',
    marginHorizontal: 12,
    marginBottom: 12,
    borderRadius: 12,
    overflow: 'hidden',
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
  },
  infoIconContainer: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#ecf0f1',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  infoContent: {
    flex: 1,
  },
  infoLabel: {
    fontSize: 12,
    color: '#666',
    marginBottom: 2,
  },
  infoValue: {
    fontSize: 15,
    color: '#333',
    fontWeight: '500',
  },
  infoValueLink: {
    color: '#3498db',
  },
  divider: {
    height: 1,
    backgroundColor: '#ecf0f1',
    marginLeft: 64,
  },
  // Description card
  descriptionCard: {
    backgroundColor: '#fff',
    marginHorizontal: 12,
    marginBottom: 12,
    borderRadius: 12,
    padding: 16,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 12,
  },
  description: {
    fontSize: 15,
    color: '#666',
    lineHeight: 22,
  },
  // Actions card
  actionsCard: {
    backgroundColor: '#fff',
    marginHorizontal: 12,
    marginBottom: 12,
    borderRadius: 12,
    overflow: 'hidden',
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
  },
  actionButtonText: {
    fontSize: 15,
    color: '#3498db',
    marginLeft: 12,
    fontWeight: '500',
  },
  bottomSpacer: {
    height: 100,
  },
  // Bottom button
  bottomButtonContainer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: '#fff',
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: '#ecf0f1',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 5,
  },
  registerButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#3498db',
    paddingVertical: 14,
    borderRadius: 10,
  },
  registerButtonDisabled: {
    opacity: 0.7,
  },
  registerButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
  cancelButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#fff',
    paddingVertical: 14,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: '#e74c3c',
  },
  cancelButtonText: {
    color: '#e74c3c',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
  fullMessage: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 14,
  },
  fullMessageText: {
    color: '#e67e22',
    fontSize: 15,
    marginLeft: 8,
  },
});

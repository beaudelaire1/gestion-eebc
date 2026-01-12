/**
 * Events Screen - Calendar view with event markers and date selection
 * Requirements: 4.1, 4.2
 */

import React, { useEffect, useCallback, useState, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
  ScrollView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useEventsStore } from '../../stores/eventsStore';
import { Event } from '../../types/models';
import { EventsStackParamList } from '../../types/navigation';

type EventsNavigationProp = NativeStackNavigationProp<EventsStackParamList, 'EventsList'>;

// Days of week in French
const DAYS_OF_WEEK = ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'];
const MONTHS_FR = [
  'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
];

/**
 * Format date for display
 */
const formatEventTime = (startDate: string, endDate: string): string => {
  const start = new Date(startDate);
  const end = new Date(endDate);
  
  const startTime = start.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  const endTime = end.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  
  return `${startTime} - ${endTime}`;
};

/**
 * Format date for display
 */
const formatEventDate = (dateStr: string): string => {
  const date = new Date(dateStr);
  return date.toLocaleDateString('fr-FR', { 
    weekday: 'long', 
    day: 'numeric', 
    month: 'long' 
  });
};

/**
 * Get dates with events for marking on calendar
 */
const getEventDates = (events: Event[]): Set<string> => {
  const dates = new Set<string>();
  events.forEach(event => {
    const startDate = new Date(event.startDate);
    const endDate = new Date(event.endDate);
    
    // Add all dates between start and end
    const current = new Date(startDate);
    current.setHours(0, 0, 0, 0);
    const end = new Date(endDate);
    end.setHours(0, 0, 0, 0);
    
    while (current <= end) {
      dates.add(current.toISOString().split('T')[0]);
      current.setDate(current.getDate() + 1);
    }
  });
  return dates;
};

/**
 * Calendar Day Component
 */
const CalendarDay: React.FC<{
  date: Date;
  isSelected: boolean;
  isToday: boolean;
  hasEvents: boolean;
  isCurrentMonth: boolean;
  onPress: () => void;
}> = ({ date, isSelected, isToday, hasEvents, isCurrentMonth, onPress }) => {
  return (
    <TouchableOpacity
      style={[
        styles.calendarDay,
        isSelected && styles.calendarDaySelected,
        isToday && !isSelected && styles.calendarDayToday,
        !isCurrentMonth && styles.calendarDayOtherMonth,
      ]}
      onPress={onPress}
      activeOpacity={0.7}
    >
      <Text
        style={[
          styles.calendarDayText,
          isSelected && styles.calendarDayTextSelected,
          isToday && !isSelected && styles.calendarDayTextToday,
          !isCurrentMonth && styles.calendarDayTextOtherMonth,
        ]}
      >
        {date.getDate()}
      </Text>
      {hasEvents && (
        <View
          style={[
            styles.eventDot,
            isSelected && styles.eventDotSelected,
          ]}
        />
      )}
    </TouchableOpacity>
  );
};

/**
 * Calendar Component
 * Requirements: 4.1
 */
const Calendar: React.FC<{
  selectedDate: string | null;
  eventDates: Set<string>;
  onDateSelect: (date: string) => void;
}> = ({ selectedDate, eventDates, onDateSelect }) => {
  const [currentMonth, setCurrentMonth] = useState(new Date());
  
  const today = useMemo(() => {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d;
  }, []);

  // Generate calendar days for current month view
  const calendarDays = useMemo(() => {
    const year = currentMonth.getFullYear();
    const month = currentMonth.getMonth();
    
    // First day of the month
    const firstDay = new Date(year, month, 1);
    // Last day of the month
    const lastDay = new Date(year, month + 1, 0);
    
    // Start from the Sunday before the first day
    const startDate = new Date(firstDay);
    startDate.setDate(startDate.getDate() - firstDay.getDay());
    
    // End on the Saturday after the last day
    const endDate = new Date(lastDay);
    endDate.setDate(endDate.getDate() + (6 - lastDay.getDay()));
    
    const days: Date[] = [];
    const current = new Date(startDate);
    
    while (current <= endDate) {
      days.push(new Date(current));
      current.setDate(current.getDate() + 1);
    }
    
    return days;
  }, [currentMonth]);

  const goToPreviousMonth = () => {
    setCurrentMonth(prev => new Date(prev.getFullYear(), prev.getMonth() - 1, 1));
  };

  const goToNextMonth = () => {
    setCurrentMonth(prev => new Date(prev.getFullYear(), prev.getMonth() + 1, 1));
  };

  const goToToday = () => {
    setCurrentMonth(new Date());
    onDateSelect(today.toISOString().split('T')[0]);
  };

  return (
    <View style={styles.calendarContainer}>
      {/* Month navigation */}
      <View style={styles.calendarHeader}>
        <TouchableOpacity onPress={goToPreviousMonth} style={styles.calendarNavButton}>
          <Ionicons name="chevron-back" size={24} color="#3498db" />
        </TouchableOpacity>
        
        <TouchableOpacity onPress={goToToday} style={styles.monthYearContainer}>
          <Text style={styles.monthYearText}>
            {MONTHS_FR[currentMonth.getMonth()]} {currentMonth.getFullYear()}
          </Text>
        </TouchableOpacity>
        
        <TouchableOpacity onPress={goToNextMonth} style={styles.calendarNavButton}>
          <Ionicons name="chevron-forward" size={24} color="#3498db" />
        </TouchableOpacity>
      </View>

      {/* Days of week header */}
      <View style={styles.daysOfWeekRow}>
        {DAYS_OF_WEEK.map(day => (
          <View key={day} style={styles.dayOfWeekCell}>
            <Text style={styles.dayOfWeekText}>{day}</Text>
          </View>
        ))}
      </View>

      {/* Calendar grid */}
      <View style={styles.calendarGrid}>
        {calendarDays.map((date, index) => {
          const dateStr = date.toISOString().split('T')[0];
          const isCurrentMonth = date.getMonth() === currentMonth.getMonth();
          const isToday = date.getTime() === today.getTime();
          const isSelected = selectedDate === dateStr;
          const hasEvents = eventDates.has(dateStr);

          return (
            <CalendarDay
              key={index}
              date={date}
              isSelected={isSelected}
              isToday={isToday}
              hasEvents={hasEvents}
              isCurrentMonth={isCurrentMonth}
              onPress={() => onDateSelect(dateStr)}
            />
          );
        })}
      </View>
    </View>
  );
};

/**
 * Event List Item Component
 */
const EventListItem: React.FC<{
  event: Event;
  onPress: () => void;
}> = ({ event, onPress }) => {
  return (
    <TouchableOpacity style={styles.eventItem} onPress={onPress} activeOpacity={0.7}>
      <View style={styles.eventTimeContainer}>
        <Text style={styles.eventTime}>
          {formatEventTime(event.startDate, event.endDate)}
        </Text>
      </View>
      <View style={styles.eventContent}>
        <View style={styles.eventHeader}>
          <Text style={styles.eventTitle} numberOfLines={1}>{event.title}</Text>
          {event.isUserRegistered && (
            <View style={styles.registeredBadge}>
              <Ionicons name="checkmark-circle" size={16} color="#27ae60" />
            </View>
          )}
        </View>
        <Text style={styles.eventType}>{event.eventType}</Text>
        {event.location && (
          <View style={styles.eventLocationRow}>
            <Ionicons name="location-outline" size={14} color="#666" />
            <Text style={styles.eventLocation} numberOfLines={1}>{event.location}</Text>
          </View>
        )}
        {event.allowsRegistration && (
          <View style={styles.eventParticipants}>
            <Ionicons name="people-outline" size={14} color="#666" />
            <Text style={styles.eventParticipantsText}>
              {event.currentParticipants}
              {event.maxParticipants ? ` / ${event.maxParticipants}` : ''} participants
            </Text>
          </View>
        )}
      </View>
      <Ionicons name="chevron-forward" size={20} color="#ccc" />
    </TouchableOpacity>
  );
};

/**
 * Offline indicator banner
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
const EmptyState: React.FC<{ selectedDate: string | null }> = ({ selectedDate }) => (
  <View style={styles.emptyState}>
    <Ionicons name="calendar-outline" size={64} color="#ccc" />
    <Text style={styles.emptyTitle}>
      {selectedDate ? 'Aucun événement' : 'Sélectionnez une date'}
    </Text>
    <Text style={styles.emptySubtitle}>
      {selectedDate
        ? `Aucun événement prévu le ${formatEventDate(selectedDate)}`
        : 'Touchez une date sur le calendrier pour voir les événements'}
    </Text>
  </View>
);

/**
 * Main EventsScreen component
 * Requirements: 4.1, 4.2
 */
export const EventsScreen: React.FC = () => {
  const navigation = useNavigation<EventsNavigationProp>();
  const {
    events,
    filteredEvents,
    selectedDate,
    isLoading,
    isRefreshing,
    error,
    fetchEvents,
    setSelectedDate,
    refreshEvents,
  } = useEventsStore();

  // Compute event dates for calendar markers
  const eventDates = useMemo(() => getEventDates(events), [events]);

  // Fetch events on mount
  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  // Handle event press - navigate to detail
  const handleEventPress = useCallback(
    (eventId: number) => {
      navigation.navigate('EventDetail', { eventId });
    },
    [navigation]
  );

  // Handle pull-to-refresh
  const handleRefresh = useCallback(() => {
    refreshEvents();
  }, [refreshEvents]);

  // Handle date selection
  const handleDateSelect = useCallback(
    (date: string) => {
      // Toggle selection if same date is tapped
      if (selectedDate === date) {
        setSelectedDate(null);
      } else {
        setSelectedDate(date);
      }
    },
    [selectedDate, setSelectedDate]
  );

  // Render event item
  const renderEventItem = useCallback(
    ({ item }: { item: Event }) => (
      <EventListItem
        event={item}
        onPress={() => handleEventPress(item.id)}
      />
    ),
    [handleEventPress]
  );

  // Key extractor for FlatList
  const keyExtractor = useCallback((item: Event) => item.id.toString(), []);

  // Show loading state on initial load
  if (isLoading && events.length === 0) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#3498db" />
        <Text style={styles.loadingText}>Chargement des événements...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Offline indicator */}
      {error && (error.includes('hors ligne') || error.includes('offline')) && (
        <OfflineBanner message={error} />
      )}

      <ScrollView
        style={styles.scrollView}
        refreshControl={
          <RefreshControl
            refreshing={isRefreshing}
            onRefresh={handleRefresh}
            colors={['#3498db']}
            tintColor="#3498db"
          />
        }
        showsVerticalScrollIndicator={false}
      >
        {/* Calendar - Requirements: 4.1 */}
        <Calendar
          selectedDate={selectedDate}
          eventDates={eventDates}
          onDateSelect={handleDateSelect}
        />

        {/* Selected date header */}
        {selectedDate && (
          <View style={styles.selectedDateHeader}>
            <Text style={styles.selectedDateText}>
              {formatEventDate(selectedDate)}
            </Text>
            <Text style={styles.eventCount}>
              {filteredEvents.length} événement{filteredEvents.length !== 1 ? 's' : ''}
            </Text>
          </View>
        )}

        {/* Events list - Requirements: 4.2 */}
        {selectedDate ? (
          filteredEvents.length > 0 ? (
            <View style={styles.eventsList}>
              {filteredEvents.map(event => (
                <EventListItem
                  key={event.id}
                  event={event}
                  onPress={() => handleEventPress(event.id)}
                />
              ))}
            </View>
          ) : (
            <EmptyState selectedDate={selectedDate} />
          )
        ) : (
          <EmptyState selectedDate={null} />
        )}
      </ScrollView>
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
  // Calendar styles
  calendarContainer: {
    backgroundColor: '#fff',
    margin: 12,
    borderRadius: 12,
    padding: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  calendarHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  calendarNavButton: {
    padding: 8,
  },
  monthYearContainer: {
    flex: 1,
    alignItems: 'center',
  },
  monthYearText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
  },
  daysOfWeekRow: {
    flexDirection: 'row',
    marginBottom: 8,
  },
  dayOfWeekCell: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 8,
  },
  dayOfWeekText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#666',
  },
  calendarGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  calendarDay: {
    width: '14.28%',
    aspectRatio: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 4,
  },
  calendarDaySelected: {
    backgroundColor: '#3498db',
    borderRadius: 20,
  },
  calendarDayToday: {
    borderWidth: 2,
    borderColor: '#3498db',
    borderRadius: 20,
  },
  calendarDayOtherMonth: {
    opacity: 0.3,
  },
  calendarDayText: {
    fontSize: 14,
    color: '#333',
  },
  calendarDayTextSelected: {
    color: '#fff',
    fontWeight: '600',
  },
  calendarDayTextToday: {
    color: '#3498db',
    fontWeight: '600',
  },
  calendarDayTextOtherMonth: {
    color: '#999',
  },
  eventDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#3498db',
    marginTop: 2,
  },
  eventDotSelected: {
    backgroundColor: '#fff',
  },
  // Selected date header
  selectedDateHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  selectedDateText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    textTransform: 'capitalize',
  },
  eventCount: {
    fontSize: 14,
    color: '#666',
  },
  // Events list
  eventsList: {
    paddingHorizontal: 12,
    paddingBottom: 20,
  },
  eventItem: {
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
  eventTimeContainer: {
    width: 70,
    marginRight: 12,
  },
  eventTime: {
    fontSize: 12,
    color: '#3498db',
    fontWeight: '500',
  },
  eventContent: {
    flex: 1,
  },
  eventHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  eventTitle: {
    flex: 1,
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  registeredBadge: {
    marginLeft: 8,
  },
  eventType: {
    fontSize: 12,
    color: '#666',
    marginBottom: 4,
    textTransform: 'capitalize',
  },
  eventLocationRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 2,
  },
  eventLocation: {
    fontSize: 12,
    color: '#666',
    marginLeft: 4,
    flex: 1,
  },
  eventParticipants: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  eventParticipantsText: {
    fontSize: 12,
    color: '#666',
    marginLeft: 4,
  },
  // Empty state
  emptyState: {
    alignItems: 'center',
    paddingVertical: 40,
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

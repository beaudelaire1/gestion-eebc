/**
 * Announcements Screen - Placeholder
 * Requirements: 6.1, 6.2, 6.5
 * Full implementation in Task 14.1
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export const AnnouncementsScreen: React.FC = () => {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Annonces</Text>
      <Text style={styles.subtitle}>Actualités de l'église</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f5f5f5',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
  },
});

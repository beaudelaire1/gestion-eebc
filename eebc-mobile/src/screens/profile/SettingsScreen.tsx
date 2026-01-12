/**
 * Settings Screen - Placeholder
 * Requirements: 10.4, 10.5, 10.6
 * Full implementation in Task 16.3
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export const SettingsScreen: React.FC = () => {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Paramètres</Text>
      <Text style={styles.subtitle}>Configuration de l'application</Text>
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

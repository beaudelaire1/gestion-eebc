/**
 * Member Detail Screen - Full member profile with contact actions
 * Requirements: 3.3, 3.4, 3.5, 3.6, 3.7
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Image,
  TouchableOpacity,
  Linking,
  Alert,
  ActivityIndicator,
  Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { RouteProp, useRoute } from '@react-navigation/native';
import { useMembersStore } from '../../stores/membersStore';
import { Member, FamilyMember } from '../../types/models';
import { MembersStackParamList } from '../../types/navigation';
import { apiService } from '../../services/ApiService';
import { ApiResponse } from '../../types/api';

type MemberDetailRouteProp = RouteProp<MembersStackParamList, 'MemberDetail'>;

/**
 * Contact action button component
 */
const ContactButton: React.FC<{
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  color: string;
  onPress: () => void;
  disabled?: boolean;
}> = ({ icon, label, color, onPress, disabled }) => (
  <TouchableOpacity
    style={[styles.contactButton, disabled && styles.contactButtonDisabled]}
    onPress={onPress}
    disabled={disabled}
    activeOpacity={0.7}
  >
    <View style={[styles.contactIconContainer, { backgroundColor: color }]}>
      <Ionicons name={icon} size={24} color="#fff" />
    </View>
    <Text style={[styles.contactLabel, disabled && styles.contactLabelDisabled]}>
      {label}
    </Text>
  </TouchableOpacity>
);

/**
 * Info row component for displaying member details
 */
const InfoRow: React.FC<{
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  value: string | undefined;
}> = ({ icon, label, value }) => {
  if (!value) return null;
  
  return (
    <View style={styles.infoRow}>
      <Ionicons name={icon} size={20} color="#3498db" style={styles.infoIcon} />
      <View style={styles.infoContent}>
        <Text style={styles.infoLabel}>{label}</Text>
        <Text style={styles.infoValue}>{value}</Text>
      </View>
    </View>
  );
};

/**
 * Section header component
 */
const SectionHeader: React.FC<{ title: string }> = ({ title }) => (
  <Text style={styles.sectionHeader}>{title}</Text>
);

/**
 * Family member item component
 */
const FamilyMemberItem: React.FC<{
  member: FamilyMember;
  onPress: () => void;
}> = ({ member, onPress }) => (
  <TouchableOpacity style={styles.familyMemberItem} onPress={onPress} activeOpacity={0.7}>
    <View style={styles.familyMemberAvatar}>
      <Text style={styles.familyMemberInitials}>
        {member.firstName.charAt(0)}{member.lastName.charAt(0)}
      </Text>
    </View>
    <View style={styles.familyMemberInfo}>
      <Text style={styles.familyMemberName}>
        {member.firstName} {member.lastName}
      </Text>
      <Text style={styles.familyMemberRelation}>{member.relationship}</Text>
    </View>
    <Ionicons name="chevron-forward" size={20} color="#ccc" />
  </TouchableOpacity>
);


/**
 * Main MemberDetailScreen component
 * Requirements: 3.3, 3.4, 3.5, 3.6, 3.7
 */
export const MemberDetailScreen: React.FC = () => {
  const route = useRoute<MemberDetailRouteProp>();
  const { memberId } = route.params;
  const getMemberById = useMembersStore((state) => state.getMemberById);
  
  const [member, setMember] = useState<Member | undefined>(getMemberById(memberId));
  const [isLoading, setIsLoading] = useState(!member);
  const [error, setError] = useState<string | null>(null);

  // Fetch member details if not in store
  useEffect(() => {
    const fetchMemberDetail = async () => {
      if (member) return;
      
      setIsLoading(true);
      try {
        const response: ApiResponse<Member> = await apiService.get(`/members/${memberId}/`);
        if (response.success) {
          setMember(response.data);
        } else {
          setError(response.error ?? 'Erreur lors du chargement');
        }
      } catch (err) {
        setError('Erreur de connexion');
      } finally {
        setIsLoading(false);
      }
    };

    fetchMemberDetail();
  }, [memberId, member]);

  /**
   * Handle phone call action
   * Requirements: 3.4
   */
  const handleCall = useCallback(() => {
    if (!member?.phone) return;
    
    const phoneUrl = Platform.OS === 'ios' 
      ? `telprompt:${member.phone}` 
      : `tel:${member.phone}`;
    
    Linking.canOpenURL(phoneUrl).then((supported) => {
      if (supported) {
        Linking.openURL(phoneUrl);
      } else {
        Alert.alert('Erreur', 'Impossible de passer un appel');
      }
    });
  }, [member?.phone]);

  /**
   * Handle WhatsApp action
   * Requirements: 3.5
   */
  const handleWhatsApp = useCallback(() => {
    const whatsappNumber = member?.whatsappNumber ?? member?.phone;
    if (!whatsappNumber) return;
    
    // Remove non-numeric characters and add country code if needed
    const cleanNumber = whatsappNumber.replace(/\D/g, '');
    const whatsappUrl = `whatsapp://send?phone=${cleanNumber}`;
    
    Linking.canOpenURL(whatsappUrl).then((supported) => {
      if (supported) {
        Linking.openURL(whatsappUrl);
      } else {
        Alert.alert(
          'WhatsApp non disponible',
          'WhatsApp n\'est pas installé sur cet appareil'
        );
      }
    });
  }, [member?.whatsappNumber, member?.phone]);

  /**
   * Handle email action
   * Requirements: 3.6
   */
  const handleEmail = useCallback(() => {
    if (!member?.email) return;
    
    const emailUrl = `mailto:${member.email}`;
    
    Linking.canOpenURL(emailUrl).then((supported) => {
      if (supported) {
        Linking.openURL(emailUrl);
      } else {
        Alert.alert('Erreur', 'Impossible d\'ouvrir l\'application email');
      }
    });
  }, [member?.email]);

  /**
   * Handle family member press - navigate to their profile
   */
  const handleFamilyMemberPress = useCallback((familyMemberId: number) => {
    // Navigate to family member's profile
    // This would require navigation prop, but for now we'll just show an alert
    Alert.alert('Navigation', `Voir le profil du membre ${familyMemberId}`);
  }, []);

  // Format date for display
  const formatDate = (dateString: string | undefined): string => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  };

  // Calculate age from date of birth
  const calculateAge = (dateOfBirth: string | undefined): string => {
    if (!dateOfBirth) return '';
    const today = new Date();
    const birthDate = new Date(dateOfBirth);
    let age = today.getFullYear() - birthDate.getFullYear();
    const monthDiff = today.getMonth() - birthDate.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
      age--;
    }
    return `${age} ans`;
  };

  // Loading state
  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#3498db" />
        <Text style={styles.loadingText}>Chargement du profil...</Text>
      </View>
    );
  }

  // Error state
  if (error || !member) {
    return (
      <View style={styles.errorContainer}>
        <Ionicons name="alert-circle-outline" size={64} color="#e74c3c" />
        <Text style={styles.errorTitle}>Erreur</Text>
        <Text style={styles.errorMessage}>{error ?? 'Membre non trouvé'}</Text>
      </View>
    );
  }

  const fullName = `${member.firstName} ${member.lastName}`;
  const initials = `${member.firstName.charAt(0)}${member.lastName.charAt(0)}`.toUpperCase();
  const hasPhone = !!member.phone;
  const hasWhatsApp = !!(member.whatsappNumber ?? member.phone);
  const hasEmail = !!member.email;

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      {/* Profile Header */}
      <View style={styles.header}>
        <View style={styles.avatarLarge}>
          {member.photo ? (
            <Image source={{ uri: member.photo }} style={styles.avatarImage} />
          ) : (
            <View style={styles.avatarPlaceholder}>
              <Text style={styles.avatarInitialsLarge}>{initials}</Text>
            </View>
          )}
        </View>
        <Text style={styles.memberName}>{fullName}</Text>
        <View style={styles.statusBadge}>
          <Text style={styles.statusText}>
            {member.status === 'active' ? 'Membre actif' : 
             member.status === 'visitor' ? 'Visiteur' : 'Inactif'}
          </Text>
        </View>
      </View>

      {/* Contact Actions - Requirements: 3.4, 3.5, 3.6 */}
      <View style={styles.contactActions}>
        <ContactButton
          icon="call"
          label="Appeler"
          color="#27ae60"
          onPress={handleCall}
          disabled={!hasPhone}
        />
        <ContactButton
          icon="logo-whatsapp"
          label="WhatsApp"
          color="#25D366"
          onPress={handleWhatsApp}
          disabled={!hasWhatsApp}
        />
        <ContactButton
          icon="mail"
          label="Email"
          color="#3498db"
          onPress={handleEmail}
          disabled={!hasEmail}
        />
      </View>

      {/* Contact Information */}
      <View style={styles.section}>
        <SectionHeader title="Coordonnées" />
        <View style={styles.card}>
          <InfoRow icon="call-outline" label="Téléphone" value={member.phone} />
          <InfoRow icon="logo-whatsapp" label="WhatsApp" value={member.whatsappNumber} />
          <InfoRow icon="mail-outline" label="Email" value={member.email} />
          <InfoRow icon="location-outline" label="Adresse" value={member.address} />
          <InfoRow icon="business-outline" label="Ville" value={member.city} />
          <InfoRow icon="map-outline" label="Code postal" value={member.postalCode} />
        </View>
      </View>

      {/* Personal Information */}
      <View style={styles.section}>
        <SectionHeader title="Informations personnelles" />
        <View style={styles.card}>
          <InfoRow 
            icon="calendar-outline" 
            label="Date de naissance" 
            value={member.dateOfBirth ? `${formatDate(member.dateOfBirth)} (${calculateAge(member.dateOfBirth)})` : undefined} 
          />
          <InfoRow 
            icon="person-outline" 
            label="Genre" 
            value={member.gender === 'M' ? 'Homme' : 'Femme'} 
          />
          <InfoRow icon="heart-outline" label="Situation" value={member.maritalStatus} />
        </View>
      </View>

      {/* Church Information */}
      <View style={styles.section}>
        <SectionHeader title="Informations église" />
        <View style={styles.card}>
          <InfoRow icon="id-card-outline" label="N° membre" value={member.memberId} />
          <InfoRow icon="home-outline" label="Site" value={member.site?.name} />
          <InfoRow 
            icon="water-outline" 
            label="Baptême" 
            value={member.isBaptized ? `Oui${member.baptismDate ? ` (${formatDate(member.baptismDate)})` : ''}` : 'Non'} 
          />
        </View>
      </View>

      {/* Family Information - Requirements: 3.3 */}
      {member.family && member.family.members.length > 0 && (
        <View style={styles.section}>
          <SectionHeader title={`Famille ${member.family.name}`} />
          <View style={styles.card}>
            <Text style={styles.familyRole}>
              Rôle: {member.family.role === 'head' ? 'Chef de famille' :
                     member.family.role === 'spouse' ? 'Conjoint(e)' :
                     member.family.role === 'child' ? 'Enfant' : 'Autre'}
            </Text>
            {member.family.members.map((familyMember) => (
              <FamilyMemberItem
                key={familyMember.id}
                member={familyMember}
                onPress={() => handleFamilyMemberPress(familyMember.id)}
              />
            ))}
          </View>
        </View>
      )}

      {/* Bottom spacing */}
      <View style={styles.bottomSpacer} />
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
    marginTop: 12,
    fontSize: 16,
    color: '#666',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f5f5f5',
    paddingHorizontal: 32,
  },
  errorTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
    marginTop: 16,
    marginBottom: 8,
  },
  errorMessage: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
  },
  header: {
    alignItems: 'center',
    paddingVertical: 24,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  avatarLarge: {
    marginBottom: 16,
  },
  avatarImage: {
    width: 100,
    height: 100,
    borderRadius: 50,
  },
  avatarPlaceholder: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: '#3498db',
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarInitialsLarge: {
    color: '#fff',
    fontSize: 36,
    fontWeight: 'bold',
  },
  memberName: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 8,
  },
  statusBadge: {
    backgroundColor: '#e8f5e9',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  statusText: {
    color: '#27ae60',
    fontSize: 14,
    fontWeight: '500',
  },
  contactActions: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingVertical: 20,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  contactButton: {
    alignItems: 'center',
  },
  contactButtonDisabled: {
    opacity: 0.4,
  },
  contactIconContainer: {
    width: 50,
    height: 50,
    borderRadius: 25,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 8,
  },
  contactLabel: {
    fontSize: 12,
    color: '#333',
    fontWeight: '500',
  },
  contactLabelDisabled: {
    color: '#999',
  },
  section: {
    marginTop: 16,
    paddingHorizontal: 16,
  },
  sectionHeader: {
    fontSize: 16,
    fontWeight: '600',
    color: '#666',
    marginBottom: 8,
    marginLeft: 4,
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  infoIcon: {
    marginRight: 12,
    marginTop: 2,
  },
  infoContent: {
    flex: 1,
  },
  infoLabel: {
    fontSize: 12,
    color: '#999',
    marginBottom: 2,
  },
  infoValue: {
    fontSize: 15,
    color: '#333',
  },
  familyRole: {
    fontSize: 14,
    color: '#666',
    marginBottom: 12,
    fontStyle: 'italic',
  },
  familyMemberItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
  },
  familyMemberAvatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#9b59b6',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  familyMemberInitials: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
  },
  familyMemberInfo: {
    flex: 1,
  },
  familyMemberName: {
    fontSize: 15,
    fontWeight: '500',
    color: '#333',
  },
  familyMemberRelation: {
    fontSize: 13,
    color: '#666',
  },
  bottomSpacer: {
    height: 32,
  },
});

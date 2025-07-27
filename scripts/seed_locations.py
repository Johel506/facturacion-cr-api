#!/usr/bin/env python3
"""
Geographic Locations Seeding Script

This script seeds the database with official Costa Rican geographic data
including provinces, cantons, and districts for proper address validation
in electronic invoicing system.

Costa Rica has 7 provinces, each with multiple cantons, and each canton
has multiple districts. This data is essential for address validation.

Requirements: 12.1, 12.2, 12.3
"""
import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.database import Base
from app.models.geographic_location import GeographicLocation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LocationSeeder:
    """Geographic locations seeding utility"""
    
    def __init__(self, database_url: str = None):
        """
        Initialize the location seeder
        
        Args:
            database_url: Database connection URL (defaults to settings)
        """
        self.database_url = database_url or settings.DATABASE_URL
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self):
        """Create database tables if they don't exist"""
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully")
    
    def seed_costa_rica_locations(self) -> int:
        """
        Seed database with official Costa Rican geographic data
        
        Returns:
            Number of locations created
        """
        logger.info("Starting Costa Rica geographic locations seeding...")
        
        # Official Costa Rican geographic data
        # This is a comprehensive but not exhaustive list of major locations
        locations_data = [
            # SAN JOSÉ PROVINCE (1)
            # San José Canton (01)
            (1, 1, 1, "San José", "San José", "Carmen", True, True),
            (1, 1, 2, "San José", "San José", "Merced", False, False),
            (1, 1, 3, "San José", "San José", "Hospital", False, False),
            (1, 1, 4, "San José", "San José", "Catedral", False, False),
            (1, 1, 5, "San José", "San José", "Zapote", False, False),
            (1, 1, 6, "San José", "San José", "San Francisco de Dos Ríos", False, False),
            (1, 1, 7, "San José", "San José", "Uruca", False, False),
            (1, 1, 8, "San José", "San José", "Mata Redonda", False, False),
            (1, 1, 9, "San José", "San José", "Pavas", False, False),
            (1, 1, 10, "San José", "San José", "Hatillo", False, False),
            (1, 1, 11, "San José", "San José", "San Sebastián", False, False),
            
            # Escazú Canton (02)
            (1, 2, 1, "San José", "Escazú", "Escazú", True, False),
            (1, 2, 2, "San José", "Escazú", "San Antonio", False, False),
            (1, 2, 3, "San José", "Escazú", "San Rafael", False, False),
            
            # Desamparados Canton (03)
            (1, 3, 1, "San José", "Desamparados", "Desamparados", True, False),
            (1, 3, 2, "San José", "Desamparados", "San Miguel", False, False),
            (1, 3, 3, "San José", "Desamparados", "San Juan de Dios", False, False),
            (1, 3, 4, "San José", "Desamparados", "San Rafael Arriba", False, False),
            (1, 3, 5, "San José", "Desamparados", "San Antonio", False, False),
            
            # Puriscal Canton (04)
            (1, 4, 1, "San José", "Puriscal", "Santiago", True, False),
            (1, 4, 2, "San José", "Puriscal", "Mercedes Sur", False, False),
            (1, 4, 3, "San José", "Puriscal", "Barbacoas", False, False),
            
            # Tarrazú Canton (05)
            (1, 5, 1, "San José", "Tarrazú", "San Marcos", True, False),
            (1, 5, 2, "San José", "Tarrazú", "San Lorenzo", False, False),
            (1, 5, 3, "San José", "Tarrazú", "San Carlos", False, False),
            
            # Aserrí Canton (06)
            (1, 6, 1, "San José", "Aserrí", "Aserrí", True, False),
            (1, 6, 2, "San José", "Aserrí", "Tarbaca", False, False),
            (1, 6, 3, "San José", "Aserrí", "Vuelta de Jorco", False, False),
            
            # Mora Canton (07)
            (1, 7, 1, "San José", "Mora", "Colón", True, False),
            (1, 7, 2, "San José", "Mora", "Guayabo", False, False),
            (1, 7, 3, "San José", "Mora", "Tabarcia", False, False),
            
            # Goicoechea Canton (08)
            (1, 8, 1, "San José", "Goicoechea", "Guadalupe", True, False),
            (1, 8, 2, "San José", "Goicoechea", "San Francisco", False, False),
            (1, 8, 3, "San José", "Goicoechea", "Calle Blancos", False, False),
            (1, 8, 4, "San José", "Goicoechea", "Mata de Plátano", False, False),
            (1, 8, 5, "San José", "Goicoechea", "Ipís", False, False),
            
            # Santa Ana Canton (09)
            (1, 9, 1, "San José", "Santa Ana", "Santa Ana", True, False),
            (1, 9, 2, "San José", "Santa Ana", "Salitral", False, False),
            (1, 9, 3, "San José", "Santa Ana", "Pozos", False, False),
            (1, 9, 4, "San José", "Santa Ana", "Uruca", False, False),
            (1, 9, 5, "San José", "Santa Ana", "Piedades", False, False),
            (1, 9, 6, "San José", "Santa Ana", "Brasil", False, False),
            
            # Alajuelita Canton (10)
            (1, 10, 1, "San José", "Alajuelita", "Alajuelita", True, False),
            (1, 10, 2, "San José", "Alajuelita", "San Josecito", False, False),
            (1, 10, 3, "San José", "Alajuelita", "San Antonio", False, False),
            (1, 10, 4, "San José", "Alajuelita", "Concepción", False, False),
            (1, 10, 5, "San José", "Alajuelita", "San Felipe", False, False),
            
            # ALAJUELA PROVINCE (2)
            # Alajuela Canton (01)
            (2, 1, 1, "Alajuela", "Alajuela", "Alajuela", True, True),
            (2, 1, 2, "Alajuela", "Alajuela", "San José", False, False),
            (2, 1, 3, "Alajuela", "Alajuela", "Carrizal", False, False),
            (2, 1, 4, "Alajuela", "Alajuela", "San Antonio", False, False),
            (2, 1, 5, "Alajuela", "Alajuela", "Guácima", False, False),
            (2, 1, 6, "Alajuela", "Alajuela", "San Isidro", False, False),
            (2, 1, 7, "Alajuela", "Alajuela", "Sabanilla", False, False),
            (2, 1, 8, "Alajuela", "Alajuela", "San Rafael", False, False),
            (2, 1, 9, "Alajuela", "Alajuela", "Río Segundo", False, False),
            (2, 1, 10, "Alajuela", "Alajuela", "Desamparados", False, False),
            (2, 1, 11, "Alajuela", "Alajuela", "Turrúcares", False, False),
            (2, 1, 12, "Alajuela", "Alajuela", "Tambor", False, False),
            (2, 1, 13, "Alajuela", "Alajuela", "Garita", False, False),
            (2, 1, 14, "Alajuela", "Alajuela", "Sarapiquí", False, False),
            
            # San Ramón Canton (02)
            (2, 2, 1, "Alajuela", "San Ramón", "San Ramón", True, False),
            (2, 2, 2, "Alajuela", "San Ramón", "Santiago", False, False),
            (2, 2, 3, "Alajuela", "San Ramón", "San Juan", False, False),
            (2, 2, 4, "Alajuela", "San Ramón", "Piedades Norte", False, False),
            (2, 2, 5, "Alajuela", "San Ramón", "Piedades Sur", False, False),
            (2, 2, 6, "Alajuela", "San Ramón", "San Rafael", False, False),
            (2, 2, 7, "Alajuela", "San Ramón", "San Isidro", False, False),
            (2, 2, 8, "Alajuela", "San Ramón", "Ángeles", False, False),
            (2, 2, 9, "Alajuela", "San Ramón", "Alfaro", False, False),
            (2, 2, 10, "Alajuela", "San Ramón", "Volio", False, False),
            (2, 2, 11, "Alajuela", "San Ramón", "Concepción", False, False),
            (2, 2, 12, "Alajuela", "San Ramón", "Zapotal", False, False),
            (2, 2, 13, "Alajuela", "San Ramón", "Peñas Blancas", False, False),
            
            # Grecia Canton (03)
            (2, 3, 1, "Alajuela", "Grecia", "Grecia", True, False),
            (2, 3, 2, "Alajuela", "Grecia", "San Isidro", False, False),
            (2, 3, 3, "Alajuela", "Grecia", "San José", False, False),
            (2, 3, 4, "Alajuela", "Grecia", "San Roque", False, False),
            (2, 3, 5, "Alajuela", "Grecia", "Tacares", False, False),
            (2, 3, 6, "Alajuela", "Grecia", "Río Cuarto", False, False),
            (2, 3, 7, "Alajuela", "Grecia", "Puente de Piedra", False, False),
            (2, 3, 8, "Alajuela", "Grecia", "Bolívar", False, False),
            
            # San Mateo Canton (04)
            (2, 4, 1, "Alajuela", "San Mateo", "San Mateo", True, False),
            (2, 4, 2, "Alajuela", "San Mateo", "Desmonte", False, False),
            (2, 4, 3, "Alajuela", "San Mateo", "Jesús María", False, False),
            
            # Atenas Canton (05)
            (2, 5, 1, "Alajuela", "Atenas", "Atenas", True, False),
            (2, 5, 2, "Alajuela", "Atenas", "Jesús", False, False),
            (2, 5, 3, "Alajuela", "Atenas", "Mercedes", False, False),
            (2, 5, 4, "Alajuela", "Atenas", "San Isidro", False, False),
            (2, 5, 5, "Alajuela", "Atenas", "Concepción", False, False),
            (2, 5, 6, "Alajuela", "Atenas", "San José", False, False),
            (2, 5, 7, "Alajuela", "Atenas", "Santa Eulalia", False, False),
            (2, 5, 8, "Alajuela", "Atenas", "Escobal", False, False),
            
            # CARTAGO PROVINCE (3)
            # Cartago Canton (01)
            (3, 1, 1, "Cartago", "Cartago", "Oriental", True, True),
            (3, 1, 2, "Cartago", "Cartago", "Occidental", False, False),
            (3, 1, 3, "Cartago", "Cartago", "Carmen", False, False),
            (3, 1, 4, "Cartago", "Cartago", "San Nicolás", False, False),
            (3, 1, 5, "Cartago", "Cartago", "Aguacaliente", False, False),
            (3, 1, 6, "Cartago", "Cartago", "Guadalupe", False, False),
            (3, 1, 7, "Cartago", "Cartago", "Corralillo", False, False),
            (3, 1, 8, "Cartago", "Cartago", "Tierra Blanca", False, False),
            (3, 1, 9, "Cartago", "Cartago", "Dulce Nombre", False, False),
            (3, 1, 10, "Cartago", "Cartago", "Llano Grande", False, False),
            (3, 1, 11, "Cartago", "Cartago", "Quebradilla", False, False),
            
            # Paraíso Canton (02)
            (3, 2, 1, "Cartago", "Paraíso", "Paraíso", True, False),
            (3, 2, 2, "Cartago", "Paraíso", "Santiago", False, False),
            (3, 2, 3, "Cartago", "Paraíso", "Orosi", False, False),
            (3, 2, 4, "Cartago", "Paraíso", "Cachí", False, False),
            (3, 2, 5, "Cartago", "Paraíso", "Llanos de Santa Lucía", False, False),
            
            # La Unión Canton (03)
            (3, 3, 1, "Cartago", "La Unión", "Tres Ríos", True, False),
            (3, 3, 2, "Cartago", "La Unión", "San Diego", False, False),
            (3, 3, 3, "Cartago", "La Unión", "San Juan", False, False),
            (3, 3, 4, "Cartago", "La Unión", "San Rafael", False, False),
            (3, 3, 5, "Cartago", "La Unión", "Concepción", False, False),
            (3, 3, 6, "Cartago", "La Unión", "Dulce Nombre", False, False),
            (3, 3, 7, "Cartago", "La Unión", "San Ramón", False, False),
            (3, 3, 8, "Cartago", "La Unión", "Río Azul", False, False),
            
            # HEREDIA PROVINCE (4)
            # Heredia Canton (01)
            (4, 1, 1, "Heredia", "Heredia", "Heredia", True, True),
            (4, 1, 2, "Heredia", "Heredia", "Mercedes", False, False),
            (4, 1, 3, "Heredia", "Heredia", "San Francisco", False, False),
            (4, 1, 4, "Heredia", "Heredia", "Ulloa", False, False),
            (4, 1, 5, "Heredia", "Heredia", "Varablanca", False, False),
            
            # Barva Canton (02)
            (4, 2, 1, "Heredia", "Barva", "Barva", True, False),
            (4, 2, 2, "Heredia", "Barva", "San Pedro", False, False),
            (4, 2, 3, "Heredia", "Barva", "San Pablo", False, False),
            (4, 2, 4, "Heredia", "Barva", "San Roque", False, False),
            (4, 2, 5, "Heredia", "Barva", "Santa Lucía", False, False),
            (4, 2, 6, "Heredia", "Barva", "San José de la Montaña", False, False),
            
            # Santo Domingo Canton (03)
            (4, 3, 1, "Heredia", "Santo Domingo", "Santo Domingo", True, False),
            (4, 3, 2, "Heredia", "Santo Domingo", "San Vicente", False, False),
            (4, 3, 3, "Heredia", "Santo Domingo", "San Miguel", False, False),
            (4, 3, 4, "Heredia", "Santo Domingo", "Paracito", False, False),
            (4, 3, 5, "Heredia", "Santo Domingo", "Santo Tomás", False, False),
            (4, 3, 6, "Heredia", "Santo Domingo", "Santa Rosa", False, False),
            (4, 3, 7, "Heredia", "Santo Domingo", "Tures", False, False),
            (4, 3, 8, "Heredia", "Santo Domingo", "Pará", False, False),
            
            # Santa Bárbara Canton (04)
            (4, 4, 1, "Heredia", "Santa Bárbara", "Santa Bárbara", True, False),
            (4, 4, 2, "Heredia", "Santa Bárbara", "San Pedro", False, False),
            (4, 4, 3, "Heredia", "Santa Bárbara", "San Juan", False, False),
            (4, 4, 4, "Heredia", "Santa Bárbara", "Jesús", False, False),
            (4, 4, 5, "Heredia", "Santa Bárbara", "Santo Domingo", False, False),
            (4, 4, 6, "Heredia", "Santa Bárbara", "Purabá", False, False),
            
            # GUANACASTE PROVINCE (5)
            # Liberia Canton (01)
            (5, 1, 1, "Guanacaste", "Liberia", "Liberia", True, True),
            (5, 1, 2, "Guanacaste", "Liberia", "Cañas Dulces", False, False),
            (5, 1, 3, "Guanacaste", "Liberia", "Mayorga", False, False),
            (5, 1, 4, "Guanacaste", "Liberia", "Nacascolo", False, False),
            (5, 1, 5, "Guanacaste", "Liberia", "Curubandé", False, False),
            
            # Nicoya Canton (02)
            (5, 2, 1, "Guanacaste", "Nicoya", "Nicoya", True, False),
            (5, 2, 2, "Guanacaste", "Nicoya", "Mansión", False, False),
            (5, 2, 3, "Guanacaste", "Nicoya", "San Antonio", False, False),
            (5, 2, 4, "Guanacaste", "Nicoya", "Quebrada Honda", False, False),
            (5, 2, 5, "Guanacaste", "Nicoya", "Sámara", False, False),
            (5, 2, 6, "Guanacaste", "Nicoya", "Nosara", False, False),
            (5, 2, 7, "Guanacaste", "Nicoya", "Belén de Nosarita", False, False),
            
            # Santa Cruz Canton (03)
            (5, 3, 1, "Guanacaste", "Santa Cruz", "Santa Cruz", True, False),
            (5, 3, 2, "Guanacaste", "Santa Cruz", "Bolsón", False, False),
            (5, 3, 3, "Guanacaste", "Santa Cruz", "Veintisiete de Abril", False, False),
            (5, 3, 4, "Guanacaste", "Santa Cruz", "Tempate", False, False),
            (5, 3, 5, "Guanacaste", "Santa Cruz", "Cartagena", False, False),
            (5, 3, 6, "Guanacaste", "Santa Cruz", "Cuajiniquil", False, False),
            (5, 3, 7, "Guanacaste", "Santa Cruz", "Diriá", False, False),
            (5, 3, 8, "Guanacaste", "Santa Cruz", "Cabo Velas", False, False),
            (5, 3, 9, "Guanacaste", "Santa Cruz", "Tamarindo", False, False),
            
            # PUNTARENAS PROVINCE (6)
            # Puntarenas Canton (01)
            (6, 1, 1, "Puntarenas", "Puntarenas", "Puntarenas", True, True),
            (6, 1, 2, "Puntarenas", "Puntarenas", "Pitahaya", False, False),
            (6, 1, 3, "Puntarenas", "Puntarenas", "Chomes", False, False),
            (6, 1, 4, "Puntarenas", "Puntarenas", "Lepanto", False, False),
            (6, 1, 5, "Puntarenas", "Puntarenas", "Paquera", False, False),
            (6, 1, 6, "Puntarenas", "Puntarenas", "Manzanillo", False, False),
            (6, 1, 7, "Puntarenas", "Puntarenas", "Guacimal", False, False),
            (6, 1, 8, "Puntarenas", "Puntarenas", "Barranca", False, False),
            (6, 1, 9, "Puntarenas", "Puntarenas", "Monteverde", False, False),
            (6, 1, 10, "Puntarenas", "Puntarenas", "Isla del Coco", False, False),
            (6, 1, 11, "Puntarenas", "Puntarenas", "Cóbano", False, False),
            (6, 1, 12, "Puntarenas", "Puntarenas", "Chacarita", False, False),
            (6, 1, 13, "Puntarenas", "Puntarenas", "Chira", False, False),
            (6, 1, 14, "Puntarenas", "Puntarenas", "Acapulco", False, False),
            (6, 1, 15, "Puntarenas", "Puntarenas", "El Roble", False, False),
            (6, 1, 16, "Puntarenas", "Puntarenas", "Arancibia", False, False),
            
            # Esparza Canton (02)
            (6, 2, 1, "Puntarenas", "Esparza", "Espíritu Santo", True, False),
            (6, 2, 2, "Puntarenas", "Esparza", "San Juan Grande", False, False),
            (6, 2, 3, "Puntarenas", "Esparza", "Macacona", False, False),
            (6, 2, 4, "Puntarenas", "Esparza", "San Rafael", False, False),
            (6, 2, 5, "Puntarenas", "Esparza", "San Jerónimo", False, False),
            (6, 2, 6, "Puntarenas", "Esparza", "Caldera", False, False),
            
            # Buenos Aires Canton (03)
            (6, 3, 1, "Puntarenas", "Buenos Aires", "Buenos Aires", True, False),
            (6, 3, 2, "Puntarenas", "Buenos Aires", "Volcán", False, False),
            (6, 3, 3, "Puntarenas", "Buenos Aires", "Potrero Grande", False, False),
            (6, 3, 4, "Puntarenas", "Buenos Aires", "Boruca", False, False),
            (6, 3, 5, "Puntarenas", "Buenos Aires", "Pilas", False, False),
            (6, 3, 6, "Puntarenas", "Buenos Aires", "Colinas", False, False),
            (6, 3, 7, "Puntarenas", "Buenos Aires", "Chánguena", False, False),
            (6, 3, 8, "Puntarenas", "Buenos Aires", "Biolley", False, False),
            (6, 3, 9, "Puntarenas", "Buenos Aires", "Brunka", False, False),
            
            # LIMÓN PROVINCE (7)
            # Limón Canton (01)
            (7, 1, 1, "Limón", "Limón", "Limón", True, True),
            (7, 1, 2, "Limón", "Limón", "Valle La Estrella", False, False),
            (7, 1, 3, "Limón", "Limón", "Río Blanco", False, False),
            (7, 1, 4, "Limón", "Limón", "Matama", False, False),
            
            # Pococí Canton (02)
            (7, 2, 1, "Limón", "Pococí", "Guápiles", True, False),
            (7, 2, 2, "Limón", "Pococí", "Jiménez", False, False),
            (7, 2, 3, "Limón", "Pococí", "Rita", False, False),
            (7, 2, 4, "Limón", "Pococí", "Roxana", False, False),
            (7, 2, 5, "Limón", "Pococí", "Cariari", False, False),
            (7, 2, 6, "Limón", "Pococí", "Colorado", False, False),
            (7, 2, 7, "Limón", "Pococí", "La Colonia", False, False),
            
            # Siquirres Canton (03)
            (7, 3, 1, "Limón", "Siquirres", "Siquirres", True, False),
            (7, 3, 2, "Limón", "Siquirres", "Pacuarito", False, False),
            (7, 3, 3, "Limón", "Siquirres", "Florida", False, False),
            (7, 3, 4, "Limón", "Siquirres", "Germania", False, False),
            (7, 3, 5, "Limón", "Siquirres", "El Cairo", False, False),
            (7, 3, 6, "Limón", "Siquirres", "Alegría", False, False),
            
            # Talamanca Canton (04)
            (7, 4, 1, "Limón", "Talamanca", "Bratsi", True, False),
            (7, 4, 2, "Limón", "Talamanca", "Sixaola", False, False),
            (7, 4, 3, "Limón", "Talamanca", "Cahuita", False, False),
            (7, 4, 4, "Limón", "Talamanca", "Telire", False, False),
            
            # Matina Canton (05)
            (7, 5, 1, "Limón", "Matina", "Matina", True, False),
            (7, 5, 2, "Limón", "Matina", "Batán", False, False),
            (7, 5, 3, "Limón", "Matina", "Carrandi", False, False),
            
            # Guácimo Canton (06)
            (7, 6, 1, "Limón", "Guácimo", "Guácimo", True, False),
            (7, 6, 2, "Limón", "Guácimo", "Mercedes", False, False),
            (7, 6, 3, "Limón", "Guácimo", "Pocora", False, False),
            (7, 6, 4, "Limón", "Guácimo", "Río Jiménez", False, False),
            (7, 6, 5, "Limón", "Guácimo", "Duacarí", False, False),
        ]
        
        session = self.SessionLocal()
        created_count = 0
        
        try:
            for location_data in locations_data:
                provincia, canton, distrito, nombre_provincia, nombre_canton, nombre_distrito, cabecera_canton, cabecera_provincia = location_data
                
                # Check if location already exists
                existing = session.query(GeographicLocation).filter(
                    GeographicLocation.provincia == provincia,
                    GeographicLocation.canton == canton,
                    GeographicLocation.distrito == distrito
                ).first()
                
                if not existing:
                    # Create new location
                    location = GeographicLocation(
                        provincia=provincia,
                        canton=canton,
                        distrito=distrito,
                        nombre_provincia=nombre_provincia,
                        nombre_canton=nombre_canton,
                        nombre_distrito=nombre_distrito,
                        cabecera_canton=cabecera_canton,
                        cabecera_provincia=cabecera_provincia,
                        activo=True
                    )
                    
                    session.add(location)
                    created_count += 1
                    logger.info(f"Created location: {provincia}-{canton:02d}-{distrito:02d} - {nombre_distrito}, {nombre_canton}, {nombre_provincia}")
                else:
                    logger.info(f"Location already exists: {provincia}-{canton:02d}-{distrito:02d}")
            
            session.commit()
            logger.info(f"Successfully created {created_count} geographic locations")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error seeding geographic locations: {str(e)}")
            raise
        finally:
            session.close()
        
        return created_count
    
    def seed_from_excel(self, excel_path: str) -> int:
        """
        Seed locations from official Excel file
        
        Args:
            excel_path: Path to the official locations Excel file
            
        Returns:
            Number of locations created
        """
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas is required to read Excel files. Install with: pip install pandas openpyxl")
            return 0
        
        if not os.path.exists(excel_path):
            logger.error(f"Excel file not found: {excel_path}")
            return 0
        
        logger.info(f"Reading locations from Excel file: {excel_path}")
        
        try:
            # Read Excel file (adjust sheet name and columns as needed)
            df = pd.read_excel(excel_path, sheet_name=0)
            logger.info(f"Read {len(df)} rows from Excel file")
            
            session = self.SessionLocal()
            created_count = 0
            
            for index, row in df.iterrows():
                try:
                    # Extract data from Excel row (adjust column names as needed)
                    provincia = int(row.get('Provincia', 0))
                    canton = int(row.get('Canton', 0))
                    distrito = int(row.get('Distrito', 0))
                    nombre_provincia = str(row.get('NombreProvincia', '')).strip()
                    nombre_canton = str(row.get('NombreCanton', '')).strip()
                    nombre_distrito = str(row.get('NombreDistrito', '')).strip()
                    
                    # Validate codes
                    if not GeographicLocation.validate_codes(provincia, canton, distrito):
                        logger.warning(f"Invalid location codes: {provincia}-{canton}-{distrito}")
                        continue
                    
                    if not all([nombre_provincia, nombre_canton, nombre_distrito]):
                        logger.warning(f"Missing names for location {provincia}-{canton}-{distrito}")
                        continue
                    
                    # Check if location already exists
                    existing = session.query(GeographicLocation).filter(
                        GeographicLocation.provincia == provincia,
                        GeographicLocation.canton == canton,
                        GeographicLocation.distrito == distrito
                    ).first()
                    
                    if not existing:
                        # Create new location
                        location = GeographicLocation(
                            provincia=provincia,
                            canton=canton,
                            distrito=distrito,
                            nombre_provincia=nombre_provincia,
                            nombre_canton=nombre_canton,
                            nombre_distrito=nombre_distrito,
                            cabecera_canton=(distrito == 1),  # First district is usually canton head
                            cabecera_provincia=(provincia <= 7 and canton == 1 and distrito == 1),  # Provincial capitals
                            activo=True
                        )
                        
                        session.add(location)
                        created_count += 1
                        
                        if created_count % 100 == 0:
                            logger.info(f"Processed {created_count} locations...")
                    
                except Exception as e:
                    logger.error(f"Error processing row {index}: {str(e)}")
                    continue
            
            session.commit()
            logger.info(f"Successfully created {created_count} locations from Excel file")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error reading Excel file: {str(e)}")
            raise
        finally:
            session.close()
        
        return created_count
    
    def clear_locations(self) -> int:
        """
        Clear all locations from database
        
        Returns:
            Number of locations deleted
        """
        logger.info("Clearing all geographic locations...")
        
        session = self.SessionLocal()
        try:
            count = session.query(GeographicLocation).count()
            session.query(GeographicLocation).delete()
            session.commit()
            logger.info(f"Deleted {count} geographic locations")
            return count
        except Exception as e:
            session.rollback()
            logger.error(f"Error clearing locations: {str(e)}")
            raise
        finally:
            session.close()


def main():
    """Main function to run location seeding"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Seed geographic locations database')
    parser.add_argument('--excel', type=str, help='Path to Excel file with location data')
    parser.add_argument('--clear', action='store_true', help='Clear existing locations')
    parser.add_argument('--sample', action='store_true', help='Seed with sample data (default)')
    parser.add_argument('--database-url', type=str, help='Database URL (optional)')
    
    args = parser.parse_args()
    
    # Initialize seeder
    seeder = LocationSeeder(database_url=args.database_url)
    
    try:
        # Create tables
        seeder.create_tables()
        
        # Clear existing data if requested
        if args.clear:
            seeder.clear_locations()
        
        # Seed data
        if args.excel:
            count = seeder.seed_from_excel(args.excel)
        else:
            count = seeder.seed_costa_rica_locations()
        
        logger.info(f"Location seeding completed successfully. Created {count} locations.")
        
    except Exception as e:
        logger.error(f"Location seeding failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
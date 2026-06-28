export enum PreferenciaOptimizacion {
  MENOR_PRECIO = "MENOR_PRECIO",
  MENOR_DESPLAZAMIENTO = "MENOR_DESPLAZAMIENTO",
  BALANCEADO = "BALANCEADO",
}

export enum EstadoItem {
  PENDIENTE = "PENDIENTE",
  CONSEGUIDO = "CONSEGUIDO",
  NO_ENCONTRADO = "NO_ENCONTRADO",
  DESCARTADO = "DESCARTADO",
}

export enum EstadoCierre {
  COMPLETADA = "COMPLETADA",
  INTERRUMPIDA = "INTERRUMPIDA",
}

export enum ModalidadUbicacion {
  GEOLOCALIZACION = "GEOLOCALIZACION",
  DIRECCION = "DIRECCION",
  PUNTO_EN_MAPA = "PUNTO_EN_MAPA",
}

export interface Producto {
  id: number;
  codigoEAN: string;
  nombre: string;
  marca: string | null;
  presentacion: string | null;
  urlImagen: string | null;
}

export interface Comercio {
  id: number;
  cuit: string;
  razonSocial: string;
}

export interface Bandera {
  id: number;
  nombre: string;
  urlLogo: string | null;
}

export interface Sucursal {
  id: number;
  comercioId: number;
  nombre: string | null;
  direccion: string | null;
  localidad: string | null;
  provincia: string | null;
  latitud: number | null;
  longitud: number | null;
}

export interface Usuario {
  id: number;
  nombre: string;
  correo: string;
}

export interface ItemCarritoAnonimo {
  productoId: number;
  cantidad: number;
}

export interface ProductoResumen {
  id: number;
  codigo_ean: string;
  nombre: string;
  marca: string | null;
  presentacion: string | null;
  url_imagen: string | null;
}

export interface PrecioProducto {
  comercio_id: number;
  comercio: string;
  sucursal_id: number;
  sucursal: string;
  direccion: string | null;
  localidad: string | null;
  provincia: string | null;
  precio: number;
  fecha_vigencia: string;
  distancia_km: number | null;
  precio_minimo: boolean;
}

export interface ItemCarrito {
  id: number;
  carrito_id: number;
  producto_id: number;
  cantidad: number;
  producto?: ProductoResumen;
}

export interface Carrito {
  id: number;
  titulo: string | null;
  activo: boolean;
  cantidad_items: number;
  fecha_ultima_edicion: string;
}

export interface CarritoDetalle {
  id: number;
  titulo: string | null;
  activo: boolean;
  items: ItemCarrito[];
}

export interface AuthResponse {
  usuario: Usuario;
  token: string;
}

export interface ErrorApi {
  error: {
    codigo: string;
    mensaje: string;
    campos?: string[];
  };
}

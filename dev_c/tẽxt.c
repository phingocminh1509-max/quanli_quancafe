/*============================================================= 

 *  QUAN LY KHACH SAN - Phien ban Linked List 

 *  Cau truc: typedef → prototype → main → dinh nghia ham 

 *=============================================================*/ 

 

#include <stdio.h> 

#include <stdlib.h> 

#include <string.h> 

#include <time.h> 

 

/*------------------------------------------------------------- 

 *  CAU TRUC DU LIEU 

 *------------------------------------------------------------*/ 

typedef struct Phong { 

    char   maPhong[10]; 

    char   loaiPhong[20]; 

    float  giaTien; 

    int    trangThai;   /* 0 = trong, 1 = da thue */ 

    char   maKH[10]; 

    time_t checkIn; 

    time_t checkOut; 

    struct Phong* next; 

} Phong; 

 

typedef struct KhachHang { 

    char maKH[10]; 

    char tenKH[50]; 

    char sdt[15]; 

    struct KhachHang* next; 

} KhachHang; 

 

/* Struct phu de luu file (khong co con tro next) */ 

typedef struct { 

    char   maPhong[10]; 

    char   loaiPhong[20]; 

    float  giaTien; 

    int    trangThai; 

    char   maKH[10]; 

    time_t checkIn; 

    time_t checkOut; 

} PhongFile; 

 

typedef struct { 

    char maKH[10]; 

    char tenKH[50]; 

    char sdt[15]; 

} KhachHangFile; 

 

/*------------------------------------------------------------- 

 *  PROTOTYPE 

 *------------------------------------------------------------*/ 

 

/* --- Tao node --- */ 

Phong*     taoPhong(void); 

KhachHang* taoKH(void); 

 

/* --- Tim kiem --- */ 

Phong*     timPhong(Phong* head, const char* ma); 

KhachHang* timKH(KhachHang* head, const char* ma); 

 

/* --- CRUD phong --- */ 

void themPhong(Phong** head); 

void hienThiPhong(Phong* head); 

void suaPhong(Phong* head); 

void xoaPhong(Phong** head); 

void timKiemPhong(Phong* head); 

 

/* --- CRUD khach hang --- */ 

void themKH(KhachHang** head); 

void hienThiKH(KhachHang* head); 

 

/* --- Nghiep vu phong --- */ 

void thuePhong(Phong* dsPhong, KhachHang* dsKH); 

void traPhong(Phong* head); 

 

/* --- Sap xep (swap data, giu nguyen lien ket) --- */ 

void hoanDoi(Phong* a, Phong* b); 

void bubbleSortPhong(Phong* head); 

void selectionSortPhong(Phong* head); 

 

/* --- File --- */ 

void luuPhong(Phong* head); 

void docPhong(Phong** head); 

void luuKH(KhachHang* head); 

void docKH(KhachHang** head); 

 

/* --- Giai phong bo nho --- */ 

void giaiPhongDSPhong(Phong* head); 

void giaiPhongDSKH(KhachHang* head); 

 

/* --- Menu --- */ 

void menu(void); 

 

/*------------------------------------------------------------- 

 *  MAIN 

 *------------------------------------------------------------*/ 

int main(void) { 

    menu(); 

    return 0; 

} 

 

/*============================================================= 

 *  DINH NGHIA HAM 

 *=============================================================*/ 

 

/*------------------------------------------------------------- 

 *  TAO NODE MOI 

 *------------------------------------------------------------*/ 

Phong* taoPhong(void) { 

    Phong* p = (Phong*)malloc(sizeof(Phong)); 

    if (!p) { printf("Loi cap phat bo nho!\n"); exit(1); } 

 

    printf("Ma phong  : "); scanf("%9s", p->maPhong); 

    getchar(); 

    printf("Loai phong: "); fgets(p->loaiPhong, sizeof(p->loaiPhong), stdin); 

    p->loaiPhong[strcspn(p->loaiPhong, "\n")] = '\0'; 

    printf("Gia tien  : "); scanf("%f", &p->giaTien); 

 

    p->trangThai = 0; 

    p->maKH[0]   = '\0'; 

    p->checkIn   = 0; 

    p->checkOut  = 0; 

    p->next      = NULL; 

    return p; 

} 

 

KhachHang* taoKH(void) { 

    KhachHang* k = (KhachHang*)malloc(sizeof(KhachHang)); 

    if (!k) { printf("Loi cap phat bo nho!\n"); exit(1); } 

 

    printf("Ma KH : "); scanf("%9s", k->maKH); 

    getchar(); 

    printf("Ten KH: "); fgets(k->tenKH, sizeof(k->tenKH), stdin); 

    k->tenKH[strcspn(k->tenKH, "\n")] = '\0'; 

    printf("SDT   : "); scanf("%14s", k->sdt); 

 

    k->next = NULL; 

    return k; 

} 

 

/*------------------------------------------------------------- 

 *  TIM KIEM  (tra ve con tro node, NULL neu khong co) 

 *------------------------------------------------------------*/ 

Phong* timPhong(Phong* head, const char* ma) { 

    while (head) { 

        if (strcmp(head->maPhong, ma) == 0) return head; 

        head = head->next; 

    } 

    return NULL; 

} 

 

KhachHang* timKH(KhachHang* head, const char* ma) { 

    while (head) { 

        if (strcmp(head->maKH, ma) == 0) return head; 

        head = head->next; 

    } 

    return NULL; 

} 

 

/*------------------------------------------------------------- 

 *  CRUD PHONG 

 *------------------------------------------------------------*/ 

void themPhong(Phong** head) { 

    Phong* p = taoPhong(); 

 

    if (timPhong(*head, p->maPhong)) { 

        printf("Ma phong da ton tai!\n"); 

        free(p); 

        return; 

    } 

 

    /* Chen vao dau danh sach */ 

    p->next = *head; 

    *head   = p; 

    printf("Them phong thanh cong!\n"); 

} 

 

void hienThiPhong(Phong* head) { 

    if (!head) { printf("Danh sach phong trong!\n"); return; } 

 

    int stt = 1; 

    printf("\n%-5s %-10s %-20s %-12s %-10s %-10s", 

           "STT", "Ma Phong", "Loai Phong", "Gia Tien", "Trang Thai", "Ma KH"); 

    printf("\n------------------------------------------------------------------------"); 

    while (head) { 

        printf("\n%-5d %-10s %-20s %-12.2f %-10s %-10s", 

               stt++, 

               head->maPhong, 

               head->loaiPhong, 

               head->giaTien, 

               head->trangThai ? "Da thue" : "Trong", 

               head->trangThai ? head->maKH : "None"); 

        head = head->next; 

    } 

    printf("\n"); 

} 

 

void suaPhong(Phong* head) { 

    char ma[10]; 

    printf("Nhap ma phong can sua: "); scanf("%9s", ma); 

 

    Phong* p = timPhong(head, ma); 

    if (!p) { printf("Khong tim thay phong!\n"); return; } 

 

    getchar(); 

    printf("Loai moi: "); fgets(p->loaiPhong, sizeof(p->loaiPhong), stdin); 

    p->loaiPhong[strcspn(p->loaiPhong, "\n")] = '\0'; 

    printf("Gia moi : "); scanf("%f", &p->giaTien); 

    printf("Cap nhat thanh cong!\n"); 

} 

 

void xoaPhong(Phong** head) { 

    char ma[10]; 

    printf("Nhap ma phong can xoa: "); scanf("%9s", ma); 

 

    Phong *prev = NULL, *curr = *head; 

    while (curr && strcmp(curr->maPhong, ma) != 0) { 

        prev = curr; 

        curr = curr->next; 

    } 

 

    if (!curr)           { printf("Khong tim thay phong!\n"); return; } 

    if (curr->trangThai) { printf("Phong dang duoc thue, khong the xoa!\n"); return; } 

 

    if (!prev) *head      = curr->next; 

    else       prev->next = curr->next; 

 

    free(curr); 

    printf("Xoa phong thanh cong!\n"); 

} 

 

void timKiemPhong(Phong* head) { 

    char ma[10]; 

    printf("Nhap ma phong: "); scanf("%9s", ma); 

 

    Phong* p = timPhong(head, ma); 

    if (!p) { printf("Khong tim thay phong!\n"); return; } 

 

    printf("\n%-5s %-10s %-20s %-12s %-10s %-10s", 

           "STT", "Ma Phong", "Loai Phong", "Gia Tien", "Trang Thai", "Ma KH"); 

    printf("\n%-5s %-10s %-20s %-12.2f %-10s %-10s\n", 

           "-", 

           p->maPhong, p->loaiPhong, p->giaTien, 

           p->trangThai ? "Da thue" : "Trong", 

           p->trangThai ? p->maKH   : "None"); 

} 

 

/*------------------------------------------------------------- 

 *  CRUD KHACH HANG 

 *------------------------------------------------------------*/ 

void themKH(KhachHang** head) { 

    KhachHang* k = taoKH(); 

 

    if (timKH(*head, k->maKH)) { 

        printf("Ma KH da ton tai!\n"); 

        free(k); 

        return; 

    } 

 

    k->next = *head; 

    *head   = k; 

    printf("Them khach hang thanh cong!\n"); 

} 

 

void hienThiKH(KhachHang* head) { 

    if (!head) { printf("Danh sach khach hang trong!\n"); return; } 

 

    int stt = 1; 

    printf("\n%-5s %-10s %-25s %-15s", 

           "STT", "Ma KH", "Ten KH", "SDT"); 

    printf("\n----------------------------------------------------"); 

    while (head) { 

        printf("\n%-5d %-10s %-25s %-15s", 

               stt++, head->maKH, head->tenKH, head->sdt); 

        head = head->next; 

    } 

    printf("\n"); 

} 

 

/*------------------------------------------------------------- 

 *  NGHIEP VU PHONG 

 *------------------------------------------------------------*/ 

void thuePhong(Phong* dsPhong, KhachHang* dsKH) { 

    char maPhong[10], maKH[10]; 

 

    printf("Nhap ma phong     : "); scanf("%9s", maPhong); 

    Phong* p = timPhong(dsPhong, maPhong); 

    if (!p)           { printf("Khong tim thay phong!\n"); return; } 

    if (p->trangThai) { printf("Phong da co nguoi!\n");   return; } 

 

    printf("Nhap ma khach hang: "); scanf("%9s", maKH); 

    KhachHang* k = timKH(dsKH, maKH); 

    if (!k) { printf("Khong tim thay khach hang!\n"); return; } 

 

    p->trangThai = 1; 

    strcpy(p->maKH, maKH); 

    p->checkIn = time(NULL); 

    printf("Thue phong thanh cong! Check-in: %s", ctime(&p->checkIn)); 

} 

 

void traPhong(Phong* head) { 

    char ma[10]; 

    printf("Nhap ma phong tra: "); scanf("%9s", ma); 

 

    Phong* p = timPhong(head, ma); 

    if (!p)            { printf("Khong tim thay phong!\n");          return; } 

    if (!p->trangThai) { printf("Phong dang o trang thai trong!\n"); return; } 

 

    p->checkOut = time(NULL); 

 

    double soGiay = difftime(p->checkOut, p->checkIn); 

    int    soNgay = (int)(soGiay / 86400.0); 

    if (soNgay < 1) soNgay = 1; 

 

    float tien = (float)soNgay * p->giaTien; 

 

    printf("\n--- HOA DON TRA PHONG ---\n"); 

    printf("Phong     : %s\n",   p->maPhong); 

    printf("Khach hang: %s\n",   p->maKH); 

    printf("Check-in  : %s",     ctime(&p->checkIn)); 

    printf("Check-out : %s",     ctime(&p->checkOut)); 

    printf("So ngay   : %d\n",   soNgay); 

    printf("Gia/ngay  : %.2f\n", p->giaTien); 

    printf("Tong tien : %.2f\n", tien); 

    printf("------------------------\n"); 

 

    /* Reset phong */ 

    p->trangThai = 0; 

    p->maKH[0]   = '\0'; 

    p->checkIn   = 0; 

    p->checkOut  = 0; 

    printf("Tra phong thanh cong!\n"); 

} 

 

/*------------------------------------------------------------- 

 *  SAP XEP  (swap data giua 2 node, giu nguyen lien ket) 

 *------------------------------------------------------------*/ 

void hoanDoi(Phong* a, Phong* b) { 

    char   tmaPhong[10], tloaiPhong[20], tmaKH[10]; 

    float  tgiaTien; 

    int    ttrangThai; 

    time_t tcheckIn, tcheckOut; 

 

    strcpy(tmaPhong,   a->maPhong); 

    strcpy(tloaiPhong, a->loaiPhong); 

    strcpy(tmaKH,      a->maKH); 

    tgiaTien   = a->giaTien; 

    ttrangThai = a->trangThai; 

    tcheckIn   = a->checkIn; 

    tcheckOut  = a->checkOut; 

 

    strcpy(a->maPhong,   b->maPhong); 

    strcpy(a->loaiPhong, b->loaiPhong); 

    strcpy(a->maKH,      b->maKH); 

    a->giaTien   = b->giaTien; 

    a->trangThai = b->trangThai; 

    a->checkIn   = b->checkIn; 

    a->checkOut  = b->checkOut; 

 

    strcpy(b->maPhong,   tmaPhong); 

    strcpy(b->loaiPhong, tloaiPhong); 

    strcpy(b->maKH,      tmaKH); 

    b->giaTien   = tgiaTien; 

    b->trangThai = ttrangThai; 

    b->checkIn   = tcheckIn; 

    b->checkOut  = tcheckOut; 

} 

 

/* Bubble Sort tang dan theo gia */ 

void bubbleSortPhong(Phong* head) { 

    if (!head || !head->next) return; 

    int swapped; 

    do { 

        swapped    = 0; 

        Phong* cur = head; 

        while (cur->next) { 

            if (cur->giaTien > cur->next->giaTien) { 

                hoanDoi(cur, cur->next); 

                swapped = 1; 

            } 

            cur = cur->next; 

        } 

    } while (swapped); 

    printf("Bubble Sort: Da sap xep phong theo gia tang dan!\n"); 

} 

 

/* Selection Sort tang dan theo gia */ 

void selectionSortPhong(Phong* head) { 

    if (!head || !head->next) return; 

    for (Phong* i = head; i != NULL; i = i->next) { 

        Phong* minNode = i; 

        for (Phong* j = i->next; j != NULL; j = j->next) 

            if (j->giaTien < minNode->giaTien) 

                minNode = j; 

        if (minNode != i) 

            hoanDoi(i, minNode); 

    } 

    printf("Selection Sort: Da sap xep phong theo gia tang dan!\n"); 

} 

 

/*------------------------------------------------------------- 

 *  FILE I/O  (luu/doc nhi phan, duoi .txt) 

 *------------------------------------------------------------*/ 

void luuPhong(Phong* head) { 

    FILE* f = fopen("phong.txt", "wb"); 

    if (!f) { printf("Loi: Khong the mo file phong.txt de ghi!\n"); return; } 

 

    int dem = 0; 

    PhongFile tmp; 

    Phong* cur = head; 

 

    /* Dem so luong de luu truoc */ 

    while (cur) { dem++; cur = cur->next; } 

    fwrite(&dem, sizeof(int), 1, f); 

 

    /* Luu tung node */ 

    cur = head; 

    while (cur) { 

        strcpy(tmp.maPhong,   cur->maPhong); 

        strcpy(tmp.loaiPhong, cur->loaiPhong); 

        tmp.giaTien   = cur->giaTien; 

        tmp.trangThai = cur->trangThai; 

        strcpy(tmp.maKH, cur->maKH); 

        tmp.checkIn  = cur->checkIn; 

        tmp.checkOut = cur->checkOut; 

        fwrite(&tmp, sizeof(PhongFile), 1, f); 

        cur = cur->next; 

    } 

    fclose(f); 

    printf("Luu %d phong thanh cong!\n", dem); 

} 

 

void docPhong(Phong** head) { 

    FILE* f = fopen("phong.txt", "rb"); 

    if (!f) return; 

 

    int dem = 0; 

    fread(&dem, sizeof(int), 1, f); 

 

    PhongFile tmp; 

    for (int i = 0; i < dem; i++) { 

        if (fread(&tmp, sizeof(PhongFile), 1, f) != 1) break; 

 

        Phong* p = (Phong*)malloc(sizeof(Phong)); 

        if (!p) { printf("Loi cap phat bo nho!\n"); fclose(f); return; } 

 

        strcpy(p->maPhong,   tmp.maPhong); 

        strcpy(p->loaiPhong, tmp.loaiPhong); 

        p->giaTien   = tmp.giaTien; 

        p->trangThai = tmp.trangThai; 

        strcpy(p->maKH, tmp.maKH); 

        p->checkIn  = tmp.checkIn; 

        p->checkOut = tmp.checkOut; 

 

        /* Chen vao dau */ 

        p->next = *head; 

        *head   = p; 

    } 

    fclose(f); 

} 

 

void luuKH(KhachHang* head) { 

    FILE* f = fopen("khachhang.txt", "wb"); 

    if (!f) { printf("Loi: Khong the mo file khachhang.txt de ghi!\n"); return; } 

 

    int dem = 0; 

    KhachHangFile tmp; 

    KhachHang* cur = head; 

 

    while (cur) { dem++; cur = cur->next; } 

    fwrite(&dem, sizeof(int), 1, f); 

 

    cur = head; 

    while (cur) { 

        strcpy(tmp.maKH,  cur->maKH); 

        strcpy(tmp.tenKH, cur->tenKH); 

        strcpy(tmp.sdt,   cur->sdt); 

        fwrite(&tmp, sizeof(KhachHangFile), 1, f); 

        cur = cur->next; 

    } 

    fclose(f); 

    printf("Luu %d khach hang thanh cong!\n", dem); 

} 

 

void docKH(KhachHang** head) { 

    FILE* f = fopen("khachhang.txt", "rb"); 

    if (!f) return; 

 

    int dem = 0; 

    fread(&dem, sizeof(int), 1, f); 

 

    KhachHangFile tmp; 

    for (int i = 0; i < dem; i++) { 

        if (fread(&tmp, sizeof(KhachHangFile), 1, f) != 1) break; 

 

        KhachHang* k = (KhachHang*)malloc(sizeof(KhachHang)); 

        if (!k) { printf("Loi cap phat bo nho!\n"); fclose(f); return; } 

 

        strcpy(k->maKH,  tmp.maKH); 

        strcpy(k->tenKH, tmp.tenKH); 

        strcpy(k->sdt,   tmp.sdt); 

 

        k->next = *head; 

        *head   = k; 

    } 

    fclose(f); 

} 

 

/*------------------------------------------------------------- 

 *  GIAI PHONG BO NHO 

 *------------------------------------------------------------*/ 

void giaiPhongDSPhong(Phong* head) { 

    Phong* tmp; 

    while (head) { tmp = head; head = head->next; free(tmp); } 

} 

 

void giaiPhongDSKH(KhachHang* head) { 

    KhachHang* tmp; 

    while (head) { tmp = head; head = head->next; free(tmp); } 

} 

 

/*------------------------------------------------------------- 

 *  MENU CHINH 

 *------------------------------------------------------------*/ 

void menu(void) { 

    Phong*     dsPhong = NULL; 

    KhachHang* dsKH    = NULL; 

 

    docPhong(&dsPhong); 

    docKH(&dsKH); 

 

    int chon; 

    do { 

        printf("\n========= QUAN LY KHACH SAN ========="); 

        printf("\n   1. Them phong"); 

        printf("\n   2. Hien thi phong"); 

        printf("\n   3. Them khach hang"); 

        printf("\n   4. Hien thi khach hang"); 

        printf("\n   5. Thue phong"); 

        printf("\n   6. Tra phong"); 

        printf("\n   7. Sua phong"); 

        printf("\n   8. Xoa phong"); 

        printf("\n   9. Tim kiem phong"); 

        printf("\n  10. Sap xep phong (Bubble Sort)"); 

        printf("\n  11. Sap xep phong (Selection Sort)"); 

        printf("\n   0. Thoat"); 

        printf("\n====================================="); 

        printf("\nChon: "); 

 

        if (scanf("%d", &chon) != 1) { 

            int c; 

            while ((c = getchar()) != '\n' && c != EOF); 

            printf("Vui long nhap so tu 0 den 11!\n"); 

            chon = -1; 

            continue; 

        } 

 

        switch (chon) { 

            case  1: themPhong(&dsPhong);              break; 

            case  2: hienThiPhong(dsPhong);            break; 

            case  3: themKH(&dsKH);                    break; 

            case  4: hienThiKH(dsKH);                  break; 

            case  5: thuePhong(dsPhong, dsKH);         break; 

            case  6: traPhong(dsPhong);                 break; 

            case  7: suaPhong(dsPhong);                 break; 

            case  8: xoaPhong(&dsPhong);                break; 

            case  9: timKiemPhong(dsPhong);             break; 

            case 10: bubbleSortPhong(dsPhong);          break; 

            case 11: selectionSortPhong(dsPhong);       break; 

            case  0: 

                luuPhong(dsPhong); 

                luuKH(dsKH); 

                giaiPhongDSPhong(dsPhong); 

                giaiPhongDSKH(dsKH); 

                printf("Tam biet!\n"); 

                break; 

            default: 

                printf("Lua chon khong hop le! Vui long chon lai.\n"); 

        } 

    } while (chon != 0); 

} 
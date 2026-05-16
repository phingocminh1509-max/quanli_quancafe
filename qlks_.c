#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

typedef struct Phong {
    char maPhong[10];
    char loaiPhong[20];
    float giaTien;
    int trangThai;
    char maKH[10];

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

Phong* taoPhong() {
    Phong* p = (Phong*)malloc(sizeof(Phong));
    printf("Ma phong: "); scanf("%s", p->maPhong);
    printf("Loai phong: ");
    scanf(" %[^\n]", p->loaiPhong);
    printf("Gia tien: "); scanf("%f", &p->giaTien);
    p->trangThai = 0;
    strcpy(p->maKH, ""); // chưa có ai thuê
    p->next = NULL;
    return p;
}

KhachHang* taoKH() {
    KhachHang* k = (KhachHang*)malloc(sizeof(KhachHang));
    printf("Ma KH: "); scanf("%s", k->maKH);
    getchar();
    printf("Ten KH: ");
    
    fgets(k->tenKH, sizeof(k->tenKH), stdin);
    k->tenKH[strcspn(k->tenKH, "\n")] = 0; // xoa \n
    printf("SDT: "); scanf("%s", k->sdt);
    k->next = NULL;
    return k;
}
//tim khach
KhachHang* timKH(KhachHang* head, char ma[]) {
    while (head != NULL) {
        if (strcmp(head->maKH, ma) == 0)
            return head;
        head = head->next;
    }
    return NULL;
}
//them danh sach
int tonTaiPhong(Phong* head, char ma[]) {
    while (head != NULL) {
        if (strcmp(head->maPhong, ma) == 0)
            return 1;
        head = head->next;
    }
    return 0;
}
void themPhong(Phong** head) {
    Phong* p = taoPhong();

    if (tonTaiPhong(*head, p->maPhong)) {
        printf("Ma phong da ton tai!\n");
        free(p);
        return;
    }

    p->trangThai = 0;
    strcpy(p->maKH, "");
    p->checkIn = 0;
    p->checkOut = 0;

    p->next = *head;
    *head = p;

    printf("Them phong thanh cong!\n");
}
//them khachhang
int tonTaiKH(KhachHang* head, char ma[]) {
    while (head != NULL) {
        if (strcmp(head->maKH, ma) == 0)
            return 1;
        head = head->next;
    }
    return 0;
}
void themKH(KhachHang** head) {
    KhachHang* k = taoKH();
    if (tonTaiKH(*head, k->maKH)) {
    printf("Ma KH da ton tai!\n");
    free(k);
    return;
    }
    k->next = *head;
    *head = k;
}
//hien thi
void hienThiPhong(Phong* head) {
    printf("\n%-10s %-10s %-10s %-10s %-10s",
        "MaPhong", "Loai", "Gia", "TrangThai", "MaKH");

    while (head != NULL) {
        printf("\n%-10s %-10s %-10.2f %-10s %-10s",
            head->maPhong,
            head->loaiPhong,
            head->giaTien,
            head->trangThai ? "Da thue" : "Trong",
            head->trangThai ? head->maKH : "None");
        head = head->next;
    }
}

void hienThiKH(KhachHang* head) {
    printf("\n%-10s %-25s %-15s",
           "MaKH", "TenKH", "SDT");
    printf("\n-----------------------------------------------------");

    while (head != NULL) {
        printf("\n%-10s %-25s %-15s",
               head->maKH,
               head->tenKH,
               head->sdt);
        head = head->next;
    }
    printf("\n");
}
//tim phong
Phong* timPhong(Phong* head, char ma[]) {
    while (head != NULL) {
        if (strcmp(head->maPhong, ma) == 0)
            return head;
        head = head->next;
    }
    return NULL;
}


//tra phong
void traPhong(Phong* head) {
    char ma[10];
    printf("Nhap ma phong tra: ");
    scanf("%s", ma);

    Phong* p = timPhong(head, ma);

    if (p == NULL) {
        printf("Khong tim thay!\n");
        return;
    }

    if (p->trangThai == 0) {
        printf("Phong dang trong!\n");
        return;
    }

    // 👉 Gán check-out
    p->checkOut = time(NULL);

    // 👉 Tính số ngày
    double soGiay = difftime(p->checkOut, p->checkIn);
    int soNgay = soGiay / (60 * 60 * 24);
    if (soNgay == 0) soNgay = 1;

    // 👉 Tính tiền
    float tien = soNgay * p->giaTien;

    printf("\nSo ngay thue: %d", soNgay);
    printf("\nTong tien: %.2f\n", tien);
    printf("%s", ctime(&p->checkIn));

    // 👉 Reset phòng
    p->trangThai = 0;
    strcpy(p->maKH, "");
    p->checkIn = 0;
    p->checkOut = 0;
    
    
    printf("Da tra phong!\n");
}
//thue phong
void thuePhong(Phong* dsPhong, KhachHang* dsKH)
{
    char maPhong[10], maKH[10];

    printf("Nhap ma phong: ");
    scanf("%s", maPhong);

    Phong* p = timPhong(dsPhong, maPhong);

    if (p == NULL) {
        printf("Khong tim thay phong!\n");
        return;
    }

    if (p->trangThai == 1) {
        printf("Phong da co nguoi!\n");
        return;
    }

    printf("Nhap ma khach hang: ");
    scanf("%s", maKH);

    KhachHang* k = timKH(dsKH, maKH);

    if (k == NULL) {
        printf("Khong tim thay khach!\n");
        return;
    }

    // Gán khách vào phòng
    p->trangThai = 1;
    strcpy(p->maKH, maKH);
    p->checkIn = time(NULL);
    printf("Thue phong thanh cong!\n");
}
//sua phong
void suaPhong(Phong* head) {
    char ma[10];
    printf("Nhap ma phong can sua: ");
    scanf("%s", ma);

    Phong* p = timPhong(head, ma);

    if (p == NULL) {
        printf("Khong tim thay!\n");
        return;
    }

    getchar();
    printf("Loai moi: ");
    fgets(p->loaiPhong, sizeof(p->loaiPhong), stdin);
    p->loaiPhong[strcspn(p->loaiPhong, "\n")] = 0;

    printf("Gia moi: ");
    scanf("%f", &p->giaTien);

    printf("Da cap nhat!\n");
}
//xoa phong
void xoaPhong(Phong** head) {
    char ma[10];
    printf("Nhap ma phong can xoa: ");
    scanf("%s", ma);

    Phong *prev = NULL, *curr = *head;

    while (curr != NULL && strcmp(curr->maPhong, ma) != 0) {
        prev = curr;
        curr = curr->next;
    }

    if (curr == NULL) {
        printf("Khong tim thay!\n");
        return;
    }

    if (curr->trangThai == 1) {
        printf("Phong dang duoc thue, khong the xoa!\n");
        return;
    }

    if (prev == NULL)
        *head = curr->next;
    else
        prev->next = curr->next;

    free(curr);
    printf("Da xoa!\n");
}
//tim phong
void timKiemPhong(Phong* head) {
    char ma[10];
    printf("Nhap ma phong: ");
    scanf("%s", ma);

    Phong* p = timPhong(head, ma);

    if (p == NULL) {
        printf("Khong tim thay!\n");
        return;
    }

    printf("\n%-10s %-10s %-10.2f %-10s %-10s",
        p->maPhong,
        p->loaiPhong,
        p->giaTien,
        p->trangThai ? "Da thue" : "Trong",
        p->trangThai ? p->maKH : "None");
}
//sap xep theo gia
void hoanDoi(Phong* a, Phong* b) {
    char maPhong[10], loaiPhong[20], maKH[10];
    float giaTien;
    int trangThai;
    time_t checkIn, checkOut;

    strcpy(maPhong, a->maPhong);
    strcpy(loaiPhong, a->loaiPhong);
    strcpy(maKH, a->maKH);
    giaTien = a->giaTien;
    trangThai = a->trangThai;
    checkIn = a->checkIn;
    checkOut = a->checkOut;

    strcpy(a->maPhong, b->maPhong);
    strcpy(a->loaiPhong, b->loaiPhong);
    strcpy(a->maKH, b->maKH);
    a->giaTien = b->giaTien;
    a->trangThai = b->trangThai;
    a->checkIn = b->checkIn;
    a->checkOut = b->checkOut;

    strcpy(b->maPhong, maPhong);
    strcpy(b->loaiPhong, loaiPhong);
    strcpy(b->maKH, maKH);
    b->giaTien = giaTien;
    b->trangThai = trangThai;
    b->checkIn = checkIn;
    b->checkOut = checkOut;
}
void sapXepPhong(Phong* head) {
    if (head == NULL) return;

    for (Phong* i = head; i != NULL; i = i->next) {
        for (Phong* j = i->next; j != NULL; j = j->next) {
            if (i->giaTien > j->giaTien) {
                hoanDoi(i, j); // 👈 dùng hàm swap an toàn
            }
        }
    }

    printf("Da sap xep theo gia!\n");
}
//lưu file
typedef struct {
    char maPhong[10];
    char loaiPhong[20];
    float giaTien;
    int trangThai;
    char maKH[10];
    time_t checkIn;
    time_t checkOut;
} PhongFile;

typedef struct {
    char maKH[10];
    char tenKH[50];
    char sdt[15];
} KhachHangFile;

void luuPhong(Phong* head) {
    FILE* f = fopen("phong.dat", "wb");
    PhongFile temp;

    while (head != NULL) {
        strcpy(temp.maPhong, head->maPhong);
        strcpy(temp.loaiPhong, head->loaiPhong);
        temp.giaTien = head->giaTien;
        temp.trangThai = head->trangThai;
        strcpy(temp.maKH, head->maKH); // THÊ
        temp.checkIn = head->checkIn;
temp.checkOut = head->checkOut;

        fwrite(&temp, sizeof(PhongFile), 1, f);
        head = head->next;
    }

    fclose(f);
}
//doc file
void docPhong(Phong** head) {
    FILE* f = fopen("phong.dat", "rb");
    if (f == NULL) return;

    PhongFile temp;

    while (fread(&temp, sizeof(PhongFile), 1, f)) {
        Phong* p = (Phong*)malloc(sizeof(Phong));

        strcpy(p->maPhong, temp.maPhong);
        strcpy(p->loaiPhong, temp.loaiPhong);
        p->giaTien = temp.giaTien;
        p->trangThai = temp.trangThai;
        strcpy(p->maKH, temp.maKH); // THÊM
        p->checkIn = temp.checkIn;
p->checkOut = temp.checkOut;

        p->next = *head;
        *head = p;
    }

    fclose(f);
}
void luuKH(KhachHang* head) {
    FILE* f = fopen("khachhang.dat", "wb");
    KhachHangFile temp;

    while (head != NULL) {
        strcpy(temp.maKH, head->maKH);
        strcpy(temp.tenKH, head->tenKH);
        strcpy(temp.sdt, head->sdt);

        fwrite(&temp, sizeof(KhachHangFile), 1, f);
        head = head->next;
    }

    fclose(f);
}
void docKH(KhachHang** head) {
    FILE* f = fopen("khachhang.dat", "rb");
    if (f == NULL) return;

    KhachHangFile temp;

    while (fread(&temp, sizeof(KhachHangFile), 1, f)) {
        KhachHang* k = (KhachHang*)malloc(sizeof(KhachHang));

        strcpy(k->maKH, temp.maKH);
        strcpy(k->tenKH, temp.tenKH);
        strcpy(k->sdt, temp.sdt);

        k->next = *head;
        *head = k;
    }

    fclose(f);
}
// giai phong bo nho
void giaiPhongDSPhong(Phong* head) {
    Phong* temp;
    while (head != NULL) {
        temp = head;
        head = head->next;
        free(temp);
    }
}
void giaiPhongDSKH(KhachHang* head) {
    KhachHang* temp;
    while (head != NULL) {
        temp = head;
        head = head->next;
        free(temp);
    }
}

void menu() {
    Phong* dsPhong = NULL;
    KhachHang* dsKH = NULL;
    docPhong(&dsPhong);
    docKH(&dsKH);
    int chon;

    do {
        printf("\n===== QUAN LY KHACH SAN =====");
        printf("\n1. Them phong");
        printf("\n2. Hien thi phong");
        printf("\n3. Them khach hang");
        printf("\n4. Hien thi khach hang");
        printf("\n5. Thue phong");
        printf("\n6. Tra phong");
        printf("\n7. Sua phong");
        printf("\n8. Xoa phong");
        printf("\n9. Tim phong");
        printf("\n10. Sap xep phong theo gia");
        printf("\n0. Thoat");
        printf("\nChon: ");
        scanf("%d", &chon);

        switch (chon) {
            case 1: themPhong(&dsPhong); break;
            case 2: hienThiPhong(dsPhong); break;
            case 3: themKH(&dsKH); break;
            case 4: hienThiKH(dsKH); break;
            case 5: thuePhong(dsPhong, dsKH); break;
            case 6: traPhong(dsPhong); break;
            case 7: suaPhong(dsPhong); break;
            case 8: xoaPhong(&dsPhong); break;
            case 9: timKiemPhong(dsPhong); break;
            case 10: sapXepPhong(dsPhong); break;
            case 0: luuPhong(dsPhong);
            luuKH(dsKH);
            
            giaiPhongDSPhong(dsPhong);
            giaiPhongDSKH(dsKH);
            ; break;
        }
    } while (chon != 0);
}
int main() {
    menu();
    return 0;
}
